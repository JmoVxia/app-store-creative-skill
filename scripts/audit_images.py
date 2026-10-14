#!/usr/bin/env python3
"""只读图片规格与显式区域差异检查；报告不代表视觉或用户确认。"""
import argparse
import hashlib
import io
import json
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root"); parser.add_argument("batch"); parser.add_argument("--report", required=True)
    args = parser.parse_args(); root = Path(args.root).expanduser().resolve()
    batch = json.loads(local(root, args.batch).read_text(encoding="utf-8"))
    report_path = local(root, args.report)
    if report_path.exists() or "baselines" in report_path.relative_to(root).parts:
        raise ValueError("报告不能覆盖既有文件或写入基准")
    result = {"images": [], "comparisons": [], "errors": [], "visual_review": "not_performed"}
    if not batch.get("images") and not batch.get("comparisons"):
        raise ValueError("没有待检查对象")
    for item in batch.get("images", []):
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
                    if key in item and row[key] != item[key]:
                        raise ValueError(key + " 不符")
                for setting, actual in (("rgb8", "rgb8_png"), ("srgb", "srgb"), ("opaque", "opaque")):
                    if item.get(setting) and not row[actual]:
                        raise ValueError(setting + " 不符")
                result["images"].append(row)
        except (OSError, ValueError, KeyError) as exc:
            result["errors"].append({"path": item.get("path"), "error": str(exc)})
    for pair in batch.get("comparisons", []):
        try:
            tolerance = pair["max_channel_delta"]; fraction = pair["max_changed_fraction"]
            if not isinstance(tolerance, int) or not 0 <= tolerance <= 255 or not 0 <= fraction <= 1:
                raise ValueError("无效比较阈值")
            if not pair.get("reason") or not pair.get("regions"):
                raise ValueError("比较需要明确区域和阈值理由")
            with Image.open(local(root, pair["left"])) as left, Image.open(local(root, pair["right"])) as right:
                if left.size != right.size:
                    raise ValueError("比较图片尺寸不同")
                # 色彩空间由规格检查负责；本项比较解码像素，不隐式转换 ICC。
                left_rgb = left.convert("RGB"); right_rgb = right.convert("RGB")
                regions = []
                for rect in pair["regions"]:
                    if len(rect) != 4 or not all(isinstance(v, int) for v in rect):
                        raise ValueError("区域需要四个整数 x/y/width/height")
                    x, y, w, h = rect
                    if min(x, y) < 0 or min(w, h) <= 0 or x + w > left.width or y + h > left.height:
                        raise ValueError("比较区域超出画布")
                    difference = ImageChops.difference(left_rgb.crop((x, y, x+w, y+h)),
                                                      right_rgb.crop((x, y, x+w, y+h)))
                    bands = difference.split()
                    maximum = ImageChops.lighter(ImageChops.lighter(bands[0], bands[1]), bands[2])
                    hist = maximum.histogram()
                    changed = sum(hist[tolerance + 1:]); share = changed / (w * h)
                    regions.append({"rect": rect, "changed_pixels": changed, "changed_fraction": share,
                                    "actual_max_delta": maximum.getextrema()[1], "passed": share <= fraction})
                entry = {"left": pair["left"], "right": pair["right"], "reason": pair["reason"],
                         "byte_identical": hashlib.sha256(local(root, pair["left"]).read_bytes()).digest() ==
                                           hashlib.sha256(local(root, pair["right"]).read_bytes()).digest(),
                         "regions": regions, "passed": all(r["passed"] for r in regions)}
                result["comparisons"].append(entry)
                if not entry["passed"]:
                    result["errors"].append({"comparison": [pair["left"], pair["right"]], "error": "区域差异超出阈值"})
        except (OSError, ValueError, KeyError, TypeError) as exc:
            result["errors"].append({"comparison": [pair.get("left"), pair.get("right")], "error": str(exc)})
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
