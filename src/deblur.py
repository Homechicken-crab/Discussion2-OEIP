"""Preparation tool: user-specified linear PSF + Wiener or truncated inverse.

No automatic PSF estimation or no-reference quality ranking is implemented.
L is continuous exposure-path distance in processing-image pixels, not kernel size.
Positive angles are clockwise in image coordinates. Dependencies: NumPy, Pillow.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import itertools
import json
import platform
import subprocess
import time
from pathlib import Path

import numpy as np
import PIL
from PIL import Image, ImageOps


def motion_psf(length: float, angle: float) -> np.ndarray:
    """Midpoint integration of a centered line, bilinearly deposited on pixels."""
    if not np.isfinite(length) or length < 0 or not np.isfinite(angle):
        raise ValueError("length must be finite and >=0; angle must be finite")
    radius = int(np.ceil(length / 2)) + 1
    size = 2 * radius + 1
    psf = np.zeros((size, size), dtype=np.float64)
    samples = max(1, int(np.ceil(length * 64)))
    t = ((np.arange(samples) + 0.5) / samples - 0.5) * length
    radians = np.deg2rad(angle)
    x = radius + t * np.cos(radians)
    y = radius + t * np.sin(radians)
    ix, iy = np.floor(x).astype(int), np.floor(y).astype(int)
    dx, dy = x - ix, y - iy
    for ox, oy, weights in (
        (0, 0, (1 - dx) * (1 - dy)), (1, 0, dx * (1 - dy)),
        (0, 1, (1 - dx) * dy), (1, 1, dx * dy),
    ):
        np.add.at(psf, (iy + oy, ix + ox), weights)
    return psf / psf.sum()


def psf_to_otf(psf: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    """Zero pad, then move the small kernel's center to FFT index (0, 0)."""
    if any(p > s for p, s in zip(psf.shape, shape)):
        raise ValueError("PSF larger than processing region; revise ROI or length")
    padded = np.zeros(shape, dtype=np.float64)
    padded[:psf.shape[0], :psf.shape[1]] = psf
    padded = np.roll(padded, tuple(-(d // 2) for d in psf.shape), axis=(0, 1))
    return np.fft.fft2(padded)


def restore(image: np.ndarray, psf: np.ndarray, method: str = "wiener",
            k: float = 0.003, threshold: float = 0.02, pad: int = 64) -> np.ndarray:
    """Return unclipped float reconstruction; FFT axes are spatial only."""
    if image.ndim not in (2, 3) or min(image.shape[:2]) < 2:
        raise ValueError("Expected an image with at least two pixels on each axis")
    if not np.all(np.isfinite(image)) or pad < 0:
        raise ValueError("Input must be finite and pad must be >=0")
    widths = [(pad, pad), (pad, pad)] + ([(0, 0)] if image.ndim == 3 else [])
    expanded = np.pad(image, widths, mode="reflect") if pad else image
    transfer = psf_to_otf(psf, expanded.shape[:2])
    if method == "wiener":
        if not np.isfinite(k) or k <= 0:
            raise ValueError("K must be finite and >0")
        filt = np.conj(transfer) / (np.abs(transfer) ** 2 + k)
    elif method == "inverse":
        if not np.isfinite(threshold) or not 0 < threshold <= 1:
            raise ValueError("threshold must be in (0,1]")
        filt = np.zeros_like(transfer)
        np.divide(1, transfer, out=filt, where=np.abs(transfer) >= threshold)
    else:
        raise ValueError("Unsupported method")
    if image.ndim == 3:
        filt = filt[:, :, None]
    result = np.fft.ifft2(np.fft.fft2(expanded, axes=(0, 1)) * filt,
                          axes=(0, 1)).real
    return result[pad:-pad, pad:-pad] if pad else result


def srgb_to_linear(x: np.ndarray) -> np.ndarray:
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * x ** (1 / 2.4) - 0.055)


def save_display(path: Path, image: np.ndarray, linear: bool) -> None:
    display = linear_to_srgb(image) if linear else np.clip(image, 0, 1)
    Image.fromarray(np.round(display * 255).astype(np.uint8)).save(path)


def float_list(value: str) -> list[float]:
    try:
        result = [float(part) for part in value.split(",")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Expected comma-separated numbers") from exc
    if not result or not np.all(np.isfinite(result)):
        raise argparse.ArgumentTypeError("Expected finite numbers")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path, required=True, help="new output directory")
    parser.add_argument("--lengths", type=float_list, default=[17.0])
    parser.add_argument("--angles", type=float_list, default=[0.0])
    parser.add_argument("--ks", type=float_list, default=[0.003])
    parser.add_argument("--method", choices=["wiener", "inverse"], default="wiener")
    parser.add_argument("--threshold", type=float, default=0.02)
    parser.add_argument("--pad", type=int, default=64)
    parser.add_argument("--roi", type=str, help="x,y,width,height after EXIF orientation")
    parser.add_argument("--srgb-domain", action="store_true", help="skip linear-light conversion")
    args = parser.parse_args()
    if args.pad < 0 or any(v < 0 for v in args.lengths) or any(v <= 0 for v in args.ks):
        parser.error("pad and lengths must be >=0; K values must be >0")
    if not np.isfinite(args.threshold) or not 0 < args.threshold <= 1:
        parser.error("threshold must be in (0,1]")
    if args.out.exists():
        parser.error("output directory already exists; choose a new run directory")
    source_bytes = args.input.read_bytes()
    with Image.open(args.input) as original:
        oriented = ImageOps.exif_transpose(original).convert("RGB")
        image = np.asarray(oriented, dtype=np.float64) / 255
    original_shape = list(image.shape)
    roi = None
    if args.roi:
        try:
            x, y, width, height = [int(v) for v in args.roi.split(",")]
        except ValueError:
            parser.error("roi must be x,y,width,height with integer values")
        if min(x, y) < 0 or min(width, height) < 2 or x + width > image.shape[1] or y + height > image.shape[0]:
            parser.error("ROI outside image or too small")
        roi = [x, y, width, height]
        image = image[y:y + height, x:x + width]
    linear = not args.srgb_domain
    if linear:
        image = srgb_to_linear(image)
    if any(motion_psf(length, 0).shape[0] > min(image.shape[:2]) + 2 * args.pad for length in args.lengths):
        parser.error("PSF too large for region and padding")
    args.out.mkdir(parents=True)
    save_display(args.out / "input_display.png", image, linear)
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[1], stderr=subprocess.DEVNULL, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=Path(__file__).resolve().parents[1], stderr=subprocess.DEVNULL, text=True).strip())
    except (subprocess.SubprocessError, OSError):
        commit, dirty = None, None
    manifest = {
        "status": "candidate_outputs_not_validated_recovery",
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "git_commit": commit, "git_worktree_dirty": dirty,
        "environment": {"python": platform.python_version(), "numpy": np.__version__, "Pillow": PIL.__version__},
        "original_oriented_shape": original_shape, "roi_xywh": roi,
        "processed_shape": list(image.shape), "resized": False,
        "linear_light": linear, "pad": args.pad, "boundary": "reflect_then_periodic_fft_then_crop",
        "angle_convention": "degrees clockwise from rightward horizontal; axis modulo 180",
        "length_convention": "continuous path span in unscaled processing pixels",
        "psf_rule": "centered uniform trajectory, 64 midpoint samples/pixel, bilinear deposition, sum=1",
        "selection": None, "candidates": [],
    }
    ks = args.ks if args.method == "wiener" else [None]
    for index, (length, angle, k) in enumerate(itertools.product(args.lengths, args.angles, ks), 1):
        start = time.perf_counter()
        psf = motion_psf(length, angle)
        raw = restore(image, psf, args.method, k or 0.003, args.threshold, args.pad)
        stem = f"candidate_{index:03d}"
        np.save(args.out / f"{stem}_raw.npy", raw)
        np.save(args.out / f"{stem}_psf.npy", psf)
        save_display(args.out / f"{stem}.png", raw, linear)
        manifest["candidates"].append({
            "id": stem, "method": args.method, "length": length, "angle": angle,
            "K": k, "inverse_threshold": args.threshold if args.method == "inverse" else None,
            "out_of_range_sample_fraction": float(np.mean((raw < 0) | (raw > 1))),
            "unclipped_min": float(raw.min()), "unclipped_max": float(raw.max()),
            "seconds": time.perf_counter() - start,
        })
    (args.out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    items = ['<figure><img src="input_display.png"><figcaption>Input: same ROI and display scale</figcaption></figure>']
    for row in manifest["candidates"]:
        label = html.escape(json.dumps(row, ensure_ascii=False))
        items.append(f'<figure><a href="{row["id"]}.png"><img src="{row["id"]}.png"></a><figcaption>{label}</figcaption></figure>')
    page = '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>复原候选比较</title><style>body{font-family:system-ui;margin:30px;background:#f5f6f8;color:#192536}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:20px}figure{margin:0;background:white;padding:12px}img{width:100%;height:auto}figcaption{font-size:14px;overflow-wrap:anywhere}</style><h1>复原候选比较</h1><p>这些是待审查候选，不代表真实细节已恢复。点击图片查看原尺寸。请与输入一起检查振铃与假细节。</p><main>' + ''.join(items) + '</main></html>'
    (args.out / "compare.html").write_text(page, encoding="utf-8")
    print(f"Saved {len(manifest['candidates'])} candidates to {args.out}")


if __name__ == "__main__":
    main()
