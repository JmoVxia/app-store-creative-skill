#!/usr/bin/env python3
"""项目状态、引用指纹与确认快照；不生成用户确认，不删除文件。"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

VERSION = "0.1.0"
SCHEMA = "1.0"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def value_digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def local(root, name):
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ValueError("需要非空项目相对路径")
    result = (root / name).resolve()
    if not result.is_relative_to(root):
        raise ValueError("路径超出项目目录: " + name)
    return result


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value, replace=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if replace:
        temporary = path.with_name(path.name + ".tmp")
        with temporary.open("x", encoding="utf-8") as stream:
            stream.write(text)
        temporary.replace(path)
    else:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(text)


def identifier(value):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", value):
        raise ValueError("ID 只允许小写字母、数字和连字符，最多64位")
    return value


def check(root):
    state = load(root / "project.json")
    if state.get("schema_version") != SCHEMA:
        raise ValueError("未知项目契约版本；需要明确迁移，不能直接写入")
    assets = load(root / "assets.json").get("assets")
    if not isinstance(assets, list):
        raise ValueError("assets.json 需要 assets 数组")
    references, rounds, asset_ids = {}, {}, set()

    def reference(ref):
        path = local(root, ref.get("path"))
        sha = ref.get("sha256", "")
        if not re.fullmatch(r"[0-9a-f]{64}", sha):
            raise ValueError("引用缺少有效 SHA256: " + ref["path"])
        if not path.is_file() or digest(path) != sha:
            raise ValueError("引用缺失或发生变化: " + ref["path"])
        if ref["path"] in references and references[ref["path"]] != sha:
            raise ValueError("同一路径指向不同版本: " + ref["path"])
        references[ref["path"]] = sha

    for asset in assets:
        aid = identifier(asset["id"])
        if aid in asset_ids:
            raise ValueError("重复素材 ID: " + aid)
        asset_ids.add(aid)
        reference(asset)
    for asset in assets:
        for aid in asset.get("provenance", {}).get("inputs", []):
            if aid not in asset_ids:
                raise ValueError("素材派生链引用不存在的 ID: " + aid)

    for path in sorted((root / "rounds").glob("*.json")):
        r = load(path)
        rid = identifier(r["id"])
        if rid in rounds or path.stem != rid:
            raise ValueError("轮次 ID 重复或与文件名不符: " + rid)
        if r.get("status") not in {"draft", "review", "confirmed", "rejected"}:
            raise ValueError("未知轮次状态: " + rid)
        for ref in r.get("inputs", []) + r.get("outputs", []) + r.get("review", {}).get("artifacts", []):
            reference(ref)
        if any(aid not in asset_ids for aid in r.get("asset_ids", [])):
            raise ValueError("轮次引用了不存在的素材 ID: " + rid)
        if r["status"] == "confirmed":
            c = r.get("confirmation") or {}
            if c.get("source") != "user" or not all(c.get(k) for k in ("message", "at", "scope")):
                raise ValueError("确认轮次缺少用户原始回复、时间或范围: " + rid)
            if r.get("open_questions"):
                raise ValueError("确认轮次仍有未决问题: " + rid)
            for group in r.get("parameter_groups", []):
                if not re.fullmatch(r"[0-9a-f]{64}", r.get("parameter_sha256", {}).get(group, "")):
                    raise ValueError("已确认参数缺少确认时指纹: " + group)
        rounds[rid] = r
        references[str(path.relative_to(root))] = digest(path)

    visited, stack = set(), set()

    def visit(rid):
        if rid in stack:
            raise ValueError("轮次依赖成环: " + rid)
        if rid in visited:
            return
        stack.add(rid)
        for dep in rounds[rid].get("depends_on", []):
            if dep not in rounds:
                raise ValueError("轮次依赖不存在: " + dep)
            if rounds[rid]["status"] == "confirmed" and rounds[dep]["status"] != "confirmed":
                raise ValueError("已确认轮次依赖尚未确认: " + dep)
            visit(dep)
        stack.remove(rid)
        visited.add(rid)
    for rid in rounds:
        visit(rid)

    for group, parameter in state.get("parameters", {}).items():
        confirmed = parameter.get("confirmed_by")
        if confirmed:
            r = rounds.get(confirmed, {})
            if r.get("status") != "confirmed" or group not in r.get("parameter_groups", []):
                raise ValueError("参数确认引用无效: " + group)
            # confirmed_by 是状态指针，不参与设计值指纹。
            value = {k: v for k, v in parameter.items() if k != "confirmed_by"}
            if value_digest(value) != r.get("parameter_sha256", {}).get(group):
                raise ValueError("参数已变化但仍沿用旧确认: " + group)
    return state, assets, rounds, references


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("root"); init.add_argument("--id", required=True); init.add_argument("--name", required=True)
    new = commands.add_parser("round")
    new.add_argument("root"); new.add_argument("--id", required=True); new.add_argument("--module", required=True)
    new.add_argument("--objective", required=True)
    for command in ("validate", "status", "fingerprint", "snapshot"):
        sub = commands.add_parser(command); sub.add_argument("root")
        if command == "fingerprint":
            sub.add_argument("--path", action="append", default=[])
            sub.add_argument("--parameter", action="append", default=[])
        if command == "snapshot":
            sub.add_argument("--id", required=True); sub.add_argument("--round", required=True)
    args = parser.parse_args(); root = Path(args.root).expanduser().resolve()

    if args.command == "init":
        if any((root / p).exists() for p in ("project.json", "assets.json")):
            raise ValueError("已有项目状态，拒绝覆盖")
        state = {
            "schema_version": SCHEMA, "skill_version": VERSION,
            "project": {"id": identifier(args.id), "name": args.name, "brief": "", "evidence": []},
            "languages": {"communication": None, "app_ui": [], "store": []},
            "targets": [], "phase": "intake", "next_action": "先听用户描述，再补问并确认理解",
            "open_questions": [], "parameters": {}, "scenes": [], "environment": {},
            "specifications": [], "capabilities": {}, "active_baseline": None,
            "validation": {"source_replay": "pending", "repeat_render": "pending", "cross_app": "pending"}
        }
        write(root / "project.json", state); write(root / "assets.json", {"assets": []})
        (root / "rounds").mkdir(exist_ok=True)
        print("项目已初始化；尚无用户确认基准")
        return
    if args.command == "round":
        check(root); rid = identifier(args.id)
        value = {"id": rid, "module": args.module, "objective": args.objective, "status": "draft",
                 "depends_on": [], "inputs": [], "outputs": [], "asset_ids": [], "parameter_groups": [],
                 "parameter_sha256": {}, "decisions": [], "rejections": [], "open_questions": [],
                 "review": {"artifacts": [], "feedback": []}, "confirmation": None, "budget": {}}
        write(root / "rounds" / (rid + ".json"), value)
        print("已创建草稿轮次: " + rid); return
    if args.command == "fingerprint":
        state = load(root / "project.json")
        if state.get("schema_version") != SCHEMA:
            raise ValueError("未知契约版本")
        result = {"files": [{"path": p, "sha256": digest(local(root, p))} for p in args.path],
                  "parameter_sha256": {}}
        for name in args.parameter:
            group = state["parameters"][name]
            result["parameter_sha256"][name] = value_digest({k: v for k, v in group.items() if k != "confirmed_by"})
        print(json.dumps(result, ensure_ascii=False, indent=2)); return
    state, assets, rounds, references = check(root)
    if args.command == "snapshot":
        bid = identifier(args.id); r = rounds.get(args.round, {})
        if r.get("status") != "confirmed":
            raise ValueError("快照需要已记录真实用户确认的轮次")
        dest = root / "baselines" / bid
        if dest.exists():
            raise ValueError("基准已经存在，拒绝覆盖")
        for group in r.get("parameter_groups", []):
            if state.get("parameters", {}).get(group, {}).get("confirmed_by") != args.round:
                raise ValueError("本轮参数未正确关联确认: " + group)
        # 候选文件与草稿轮次不能成为已确认基准的依赖。
        frozen = {rid: value for rid, value in rounds.items() if value["status"] == "confirmed"}
        scoped, selected = {}, set()
        by_id = {a["id"]: a for a in assets}
        by_path = {a["path"]: a["id"] for a in assets}

        def include_asset(aid):
            if aid in selected:
                return
            selected.add(aid); asset = by_id[aid]
            scoped[asset["path"]] = asset["sha256"]
            for dep in asset.get("provenance", {}).get("inputs", []):
                include_asset(dep)

        for rid, value in frozen.items():
            scoped["rounds/" + rid + ".json"] = references["rounds/" + rid + ".json"]
            for ref in value.get("inputs", []) + value.get("outputs", []) + value.get("review", {}).get("artifacts", []):
                scoped[ref["path"]] = ref["sha256"]
                if ref["path"] in by_path:
                    include_asset(by_path[ref["path"]])
            for aid in value.get("asset_ids", []):
                include_asset(aid)
        state["active_baseline"] = bid
        write(dest / "project.json", state)
        write(dest / "assets.json", {"assets": [a for a in assets if a["id"] in selected]})
        for rid, value in frozen.items():
            write(dest / "rounds" / (rid + ".json"), value)
        snapshots = {str(p.relative_to(dest)): digest(p) for p in dest.rglob("*.json")}
        write(dest / "manifest.json", {"created_at": datetime.now(timezone.utc).isoformat(),
              "confirmed_round": args.round, "files": scoped,
              "snapshot_files": snapshots})
        write(root / "project.json", state, replace=True)
        print("基准已保存；引用文件仍需保留: " + bid); return
    drift = []
    if state.get("active_baseline"):
        base = local(root, "baselines/" + identifier(state["active_baseline"]))
        manifest = load(base / "manifest.json")
        for name, sha in manifest["files"].items():
            p = local(root, name)
            if not p.is_file() or digest(p) != sha:
                drift.append(name)
        for name, sha in manifest["snapshot_files"].items():
            snapshot = local(base, name)
            if not snapshot.is_file() or digest(snapshot) != sha:
                raise ValueError("基准快照被修改: " + name)
    result = {"project": state["project"], "phase": state["phase"],
              "baseline": state["active_baseline"], "rounds": {k: v["status"] for k, v in rounds.items()},
              "assets": len(assets), "next_action": state["next_action"],
              "open_questions": state["open_questions"], "baseline_reference_drift": drift,
              "validation": state["validation"]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.command == "validate" and drift:
        raise ValueError("基准引用发生变化，先核对影响，不可当作原版复现")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print("错误: " + str(exc), file=sys.stderr)
        sys.exit(1)
