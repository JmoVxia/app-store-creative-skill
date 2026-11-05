#!/usr/bin/env python3
"""只读图片规格与显式区域差异检查；报告不代表视觉或用户确认。"""
import argparse
import hashlib
import io
import json
import math
import os
import sys
from pathlib import Path
from PIL import Image, ImageChops, ImageCms


def local(root, name):
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ValueError("需要项目相对路径")
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        raise ValueError("路径超出项目目录: " + name)
    return path


def canonical(root, name):
    local(root, name)  # 解析真实目标仅用于越界检查，不折叠矩阵中的符号链接名称。
    return Path(os.path.abspath(root / name)).relative_to(root).as_posix()


def objects(batch, key):
    value = batch.get(key, [])
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError(key + " 需要对象数组")
    return value


def thresholds(item):
    tolerance, fraction = item["max_channel_delta"], item["max_changed_fraction"]
    if (type(tolerance) is not int or not 0 <= tolerance <= 255 or
            type(fraction) not in (int, float) or not 0 <= fraction <= 1 or not math.isfinite(fraction)):
        raise ValueError("无效比较阈值；必须显式给出数值，布尔值不算数值")
    if not isinstance(item.get("reason"), str) or not item["reason"].strip():
        raise ValueError("比较需要明确阈值理由")
    return tolerance, fraction


def selection(root, item, size, required=False):
    if "mask" not in item:
        if required or "mask_mode" in item:
            raise ValueError("需要mask及显式mask_mode")
        return None, None
    mode = item.get("mask_mode")
    if mode not in ("luminance", "alpha"):
        raise ValueError("mask_mode必须显式为luminance或alpha")
    path = local(root, item["mask"])
    data = path.read_bytes()
    with Image.open(path) as mask:
        mask.load()
        if mask.format != "PNG" or mask.size != size:
            raise ValueError("mask必须是与检查图片同尺寸的PNG")
        has_alpha = "A" in mask.getbands() or "transparency" in mask.info
        if mode == "alpha":
            if not has_alpha:
                raise ValueError("alpha模式需要mask真实含alpha通道或透明信息")
            channel = mask.convert("RGBA").getchannel("A")
        else:
            channel = mask.convert("RGB").convert("L")
        # mask仅选择像素；不按灰度加权。抗锯齿过渡带由项目构造mask时处理。
        selected = channel.point(lambda value: 255 if value > 0 else 0)
        if mode == "luminance" and has_alpha:
            # 先二值化再取交集，避免低亮度乘低alpha后8位舍入为0。
            alpha = mask.convert("RGBA").getchannel("A").point(lambda value: 255 if value > 0 else 0)
            selected = ImageChops.multiply(selected, alpha)
    return selected, {"path": item["mask"], "mode": mode,
                      "sha256": hashlib.sha256(data).hexdigest(), "selection": "value > 0; unweighted"}


def compare_regions(left, right, item, mask):
    tolerance, fraction = thresholds(item)
    if not isinstance(item.get("regions"), list) or not item["regions"]:
        raise ValueError("比较需要明确非空区域数组")
    regions = []
    for rect in item["regions"]:
        if not isinstance(rect, list) or len(rect) != 4 or not all(type(v) is int for v in rect):
            raise ValueError("区域需要四个整数 x/y/width/height；布尔值不算整数")
        x, y, w, h = rect
        if min(x, y) < 0 or min(w, h) <= 0 or x + w > left.width or y + h > left.height:
            raise ValueError("比较区域超出画布")
        box = (x, y, x + w, y + h)
        difference = ImageChops.difference(left.crop(box), right.crop(box))
        bands = difference.split()
        maximum = ImageChops.lighter(ImageChops.lighter(bands[0], bands[1]), bands[2])
        hist = maximum.histogram(mask=mask.crop(box) if mask is not None else None)
        checked = sum(hist)
        if checked == 0:
            raise ValueError("区域与mask交集为0，拒绝空覆盖: " + str(rect))
        changed = sum(hist[tolerance + 1:]); share = changed / checked
        regions.append({"rect": rect, "checked_pixels": checked, "changed_pixels": changed,
                        "changed_fraction": share,
                        "actual_max_delta": max(index for index, count in enumerate(hist) if count),
                        "passed": share <= fraction})
    return regions


def coverage_check(root, batch, image_items):
    coverage = batch["coverage"]
    if not isinstance(coverage, dict):
        raise ValueError("coverage需要对象")
    expected_items = coverage["expected_paths"]
    if not isinstance(expected_items, list) or not expected_items:
        raise ValueError("coverage.expected_paths需要非空路径数组")
    expected = [canonical(root, name) for name in expected_items]
    if len(set(expected)) != len(expected):
        raise ValueError("coverage.expected_paths存在重复路径")
    directory = root / canonical(root, coverage["directory"])
    if not directory.is_dir():
        raise ValueError("coverage.directory不是已有目录")
    pattern = coverage["glob"]
    if (not isinstance(pattern, str) or not pattern or Path(pattern).is_absolute() or
            ".." in Path(pattern).parts):
        raise ValueError("coverage.glob需要目录内的相对glob")
    reject = coverage.get("reject_identical", False)
    if type(reject) is not bool:
        raise ValueError("coverage.reject_identical需要布尔值")
    actual = {canonical(root, path.relative_to(root).as_posix())
              for path in directory.glob(pattern) if path.is_file()}
    declared = [canonical(root, item["path"]) for item in image_items]
    expected_set = set(expected)
    row = {"expected_paths": expected, "directory": coverage["directory"], "glob": pattern,
           "actual_paths": sorted(actual), "missing_files": sorted(expected_set - actual),
           "extra_files": sorted(actual - expected_set), "images_matrix_checked": "images" in batch,
           "format_constraints_checked": any(any(key in item for key in ("width", "height", "rgb8", "srgb", "opaque")) for item in image_items),
           "format_constraint_scope": {item["path"]: [key for key in ("width", "height", "rgb8", "srgb", "opaque") if key in item] for item in image_items},
           "reject_identical": reject, "byte_duplicates": [], "pixel_duplicates": []}
    if "images" in batch:
        row.update({"missing_image_entries": sorted(expected_set - set(declared)),
                    "extra_image_entries": sorted(set(declared) - expected_set),
                    "duplicate_image_entries": sorted({name for name in declared if declared.count(name) > 1})})
    file_groups, pixel_groups = {}, {}
    for name in sorted(actual | set(declared) | expected_set):
        path = local(root, name)
        if not path.is_file():
            continue
        file_groups.setdefault(hashlib.sha256(path.read_bytes()).hexdigest(), []).append(name)
        with Image.open(path) as image:
            image.load()
            decoded = image.convert("RGBA")
            digest = hashlib.sha256(str(decoded.size).encode("ascii") + b"\0" + decoded.tobytes()).hexdigest()
            pixel_groups.setdefault(digest, []).append(name)
    for field, groups in (("byte_duplicates", file_groups), ("pixel_duplicates", pixel_groups)):
        row[field] = [{"sha256": digest, "paths": names} for digest, names in groups.items() if len(names) > 1]
    row["passed"] = not any(row.get(key) for key in ("missing_files", "extra_files", "missing_image_entries",
                                                     "extra_image_entries", "duplicate_image_entries"))
    if reject and (row["byte_duplicates"] or row["pixel_duplicates"]):
        row["passed"] = False
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root"); parser.add_argument("batch"); parser.add_argument("--report", required=True)
    args = parser.parse_args(); root = Path(args.root).expanduser().resolve()
    batch = json.loads(local(root, args.batch).read_text(encoding="utf-8"))
    if not isinstance(batch, dict):
        raise ValueError("批次需要JSON对象")
    report_path = local(root, args.report)
    if report_path.exists() or "baselines" in report_path.relative_to(root).parts:
        raise ValueError("报告不能覆盖既有文件或写入基准")
    image_items, pairs = objects(batch, "images"), objects(batch, "comparisons")
    backgrounds, resources = objects(batch, "background_checks"), objects(batch, "resources")
    result = {"images": [], "comparisons": [], "background_checks": [], "resources": [],
              "errors": [], "visual_review": "not_performed"}
    if not any((image_items, pairs, backgrounds, resources, batch.get("coverage"))):
        raise ValueError("没有待检查对象")
    for item in image_items:
        try:
            p = local(root, item["path"]); data = p.read_bytes()
            with Image.open(p) as im:
                im.load()
                srgb = "srgb" in im.info
                if im.info.get("icc_profile"):
                    srgb = srgb or "srgb" in ImageCms.getProfileName(
                        ImageCms.ImageCmsProfile(io.BytesIO(im.info["icc_profile"]))).lower()
                png8rgb = data[:8] == b"\x89PNG\r\n\x1a\n" and data[24:26] == bytes([8, 2])
                row = {"path": item["path"], "width": im.width, "height": im.height,
                       "mode": im.mode, "rgb8_png": png8rgb, "srgb": srgb,
                       "opaque": "A" not in im.getbands() and "transparency" not in im.info,
                       "sha256": hashlib.sha256(data).hexdigest()}
                for key in ("width", "height"):
                    if key in item and (type(item[key]) is not int or item[key] <= 0 or row[key] != item[key]):
                        raise ValueError(key + " 不符或不是正整数")
                for setting, actual in (("rgb8", "rgb8_png"), ("srgb", "srgb"), ("opaque", "opaque")):
                    if setting in item and type(item[setting]) is not bool:
                        raise ValueError(setting + " 需要布尔值")
                    if item.get(setting) and not row[actual]:
                        raise ValueError(setting + " 不符")
                result["images"].append(row)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            result["errors"].append({"path": item.get("path"), "error": str(exc)})
    for item in resources:
        try:
            expected_hash = item["sha256"]
            if not isinstance(expected_hash, str) or len(expected_hash) != 64 or any(c not in "0123456789abcdefABCDEF" for c in expected_hash):
                raise ValueError("资源sha256需要64位十六进制字符串")
            actual_hash = hashlib.sha256(local(root, item["path"]).read_bytes()).hexdigest()
            row = {"path": item["path"], "expected_sha256": expected_hash.lower(),
                   "sha256": actual_hash, "passed": actual_hash == expected_hash.lower()}
            result["resources"].append(row)
            if not row["passed"]:
                result["errors"].append({"resource": item["path"], "error": "冻结资源哈希不符"})
        except (OSError, ValueError, KeyError, TypeError) as exc:
            result["errors"].append({"resource": item.get("path"), "error": str(exc)})
    for pair in pairs:
        try:
            with Image.open(local(root, pair["left"])) as left, Image.open(local(root, pair["right"])) as right:
                if left.size != right.size:
                    raise ValueError("比较图片尺寸不同")
                # 色彩空间由规格检查负责；本项比较解码像素，不隐式转换 ICC。
                left_rgb = left.convert("RGB"); right_rgb = right.convert("RGB")
                mask, mask_record = selection(root, pair, left.size)
                regions = compare_regions(left_rgb, right_rgb, pair, mask)
                entry = {"left": pair["left"], "right": pair["right"], "reason": pair["reason"],
                         "byte_identical": hashlib.sha256(local(root, pair["left"]).read_bytes()).digest() ==
                                           hashlib.sha256(local(root, pair["right"]).read_bytes()).digest(),
                         "regions": regions, "passed": all(r["passed"] for r in regions)}
                if mask_record is not None:
                    entry["mask"] = mask_record
                result["comparisons"].append(entry)
                if not entry["passed"]:
                    result["errors"].append({"comparison": [pair["left"], pair["right"]], "error": "区域差异超出阈值"})
        except (OSError, ValueError, KeyError, TypeError) as exc:
            result["errors"].append({"comparison": [pair.get("left"), pair.get("right")], "error": str(exc)})
    for item in backgrounds:
        try:
            color = item["color"]
            if not isinstance(color, list) or len(color) != 3 or any(type(c) is not int or not 0 <= c <= 255 for c in color):
                raise ValueError("背景color需要三个0—255整数；布尔值不算整数")
            with Image.open(local(root, item["path"])) as image:
                mask, mask_record = selection(root, item, image.size, required=True)
                regions = compare_regions(image.convert("RGB"), Image.new("RGB", image.size, tuple(color)), item, mask)
            entry = {"path": item["path"], "mask": mask_record, "color": color,
                     "reason": item["reason"], "regions": regions, "passed": all(r["passed"] for r in regions)}
            result["background_checks"].append(entry)
            if not entry["passed"]:
                result["errors"].append({"background_check": item["path"], "error": "背景区域差异超出阈值"})
        except (OSError, ValueError, KeyError, TypeError) as exc:
            result["errors"].append({"background_check": item.get("path"), "error": str(exc)})
    if "coverage" in batch:
        try:
            result["coverage"] = coverage_check(root, batch, image_items)
            if not result["coverage"]["passed"]:
                result["errors"].append({"coverage": True, "error": "矩阵、目录覆盖或重复图检查不符"})
        except (OSError, ValueError, KeyError, TypeError) as exc:
            result["errors"].append({"coverage": True, "error": str(exc)})
    result["passed"] = not result["errors"]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"passed": result["passed"], "images": len(result["images"]),
                      "comparisons": len(result["comparisons"]), "errors": result["errors"]}, ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError) as exc:
        print("错误: " + str(exc), file=sys.stderr)
        sys.exit(1)
