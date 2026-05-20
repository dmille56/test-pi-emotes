import argparse
import base64
import os
import time
from typing import Dict

from openai import OpenAI

import subprocess
import re


DEFAULT_MODEL = "gpt-image-2"
DEFAULT_SIZE = "128x128"
DEFAULT_QUALITY = "high"
DEFAULT_BACKGROUND = "opaque"


MAGICK_BIN = os.environ.get("MAGICK_BIN", "magick")


BASE_INVARIANTS = (
    "Preserve everything else exactly: character identity, monocle position, hair shape, "
    "white lab coat (including belt/patch layout), cybernetic arm design (hex plates + teal/green "
    "glowing cable style, visible only from upper arm/forearm up), and a cyber parrot always "
    "perched on the left shoulder. Preserve pose and **exact shoulder-up crop framing** (head-and-upper-shoulders; "
    "trim above mid-torso; no full body/legs). Preserve **exact pixel geometry**: keep the same zoom, scale, camera framing, and head/shoulder placement relative to the image borders (no pan/shift, no rotation). "
    "Only change the specific facial expression / mouth openness / eye state described for this filename. "
    "No extra characters. No text. No logos. No background elements added. "
)


EDIT_PROMPT_TEMPLATE = (
    "Using the provided input image as the exact character reference, change ONLY the following: {change}\n\n"
    f"{BASE_INVARIANTS}"
    "Output: square PNG with the same shoulder-up framing crop (no zoom/crop change), transparent background."
)


def save_b64_png(b64_json: str, out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(b64_json))


def _parse_fuzz_percent(fuzz: str) -> int:
    """Parse fuzz like '8%' into an integer threshold in 0..255."""
    s = fuzz.strip()
    if s.endswith("%"):
        val = float(s[:-1])
    else:
        # Allow raw percentage without % (treated as percent).
        val = float(s)
    val = max(0.0, min(100.0, val))
    return int(round(255.0 * (val / 100.0)))


def _sample_corner_rgb(in_path: str) -> tuple[int, int, int]:
    """Sample top-left pixel color in sRGB from ImageMagick (e.g. srgb(231,232,231))."""
    # Using -format keeps output stable.
    cmd = [
        MAGICK_BIN,
        in_path,
        "-format",
        "%[pixel:p{0,0}]",
        "info:",
    ]
    out = subprocess.check_output(cmd, text=True).strip()

    # ImageMagick may return either:
    # - srgb(r,g,b)
    # - srgba(r,g,b,a)
    m = re.match(r"^srgb\((\d+),(\d+),(\d+)\)$", out)
    if m:
        r, g, b = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return (r, g, b)

    m = re.match(r"^srgba\((\d+),(\d+),(\d+),[0-9.]+\)$", out)
    if m:
        r, g, b = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return (r, g, b)

    raise RuntimeError(f"Unexpected corner pixel format: {out!r}")


def remove_background(in_path: str, *, fuzz: str = "8%") -> None:
    """Remove solid-ish background by sampling the corner pixel.

    Prefer a reliable PIL+NumPy implementation. Fall back to ImageMagick if PIL
    isn't available.
    """
    bg_r, bg_g, bg_b = _sample_corner_rgb(in_path)
    thresh = _parse_fuzz_percent(fuzz)

    try:
        import numpy as np  # type: ignore
        from PIL import Image  # type: ignore

        im = Image.open(in_path).convert("RGBA")
        arr = np.array(im)
        rgb = arr[:, :, :3].astype(np.int16)
        bg = np.array([bg_r, bg_g, bg_b], dtype=np.int16)
        # L1 distance from background color.
        dist = np.abs(rgb - bg).sum(axis=2)
        mask = dist <= (thresh * 3)
        arr[:, :, 3][mask] = 0
        out = Image.fromarray(arr, mode="RGBA")
        out.save(in_path)
        return
    except Exception as e:  # noqa: BLE001
        print(f"[warn] PIL bg-removal failed for {in_path}: {e}; falling back to ImageMagick")

    # Fallback: pragmatically use ImageMagick.
    rgb = f"rgb({bg_r},{bg_g},{bg_b})"
    tmp_path = in_path + ".bgrem.png"
    cmd = [
        MAGICK_BIN,
        in_path,
        "-alpha",
        "set",
        "-alpha",
        "on",
        "-fuzz",
        fuzz,
        "-transparent-color",
        rgb,
        tmp_path,
    ]
    subprocess.check_call(cmd)
    os.replace(tmp_path, in_path)


def call_with_retries(fn, *, retries: int = 4, base_sleep_s: float = 1.5):
    last_err = None
    for i in range(retries):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            last_err = e
            sleep_s = base_sleep_s * (2**i)
            print(f"[warn] attempt {i+1}/{retries} failed: {e}. sleeping {sleep_s:.1f}s")
            time.sleep(sleep_s)
    raise last_err


def build_manifest(include_compact: bool) -> Dict[str, str]:
    """Map relative output path -> edit-specific change description."""

    manifest = {
        # hi
        "hi/hi_1.png": "Greeting variant 1: eyebrows raised and friendly expression; NO head tilt and no framing change. Parrot remains perched.",
        "hi/hi_2.png": "Greeting variant 2: bigger confident grin (mouth and cheeks only); NO head tilt and no framing change. Parrot remains perched.",
        "hi/hi_3.png": "Greeting variant 3: surprise/welcome eyes (eye state only) with neutral mouth; NO head tilt and no framing change. Parrot remains perched.",

        # idle
        "idle/idle.png": "Neutral idle expression (face only); NO pose/framing change; parrot stays perched.",
        "idle/idle_blink.png": "Idle blink: eyes closed briefly (monocle still present); mouth neutral; NO pose/framing change; parrot stays perched.",

        # think
        "think/think.png": "Thinking expression (brows/eyes and mouth only); NO pose/framing change; parrot stays perched.",
        "think/think_hard.png": "Hard thinking (brows/eyes and mouth only); cyber arm glow slightly stronger but arm position unchanged; parrot LED pulse once (no reposition). NO pose/framing change.",

        # talk (must include at least one filename containing 'close')
        "talk/talk_close.png": "Mouth closed (no open gap); keep everything else the same; parrot stays perched; NO pose/framing change.",
        "talk/talk_small.png": "Talking with small mouth opening (slight gap); parrot LED flickers lightly; NO pose/framing change.",
        "talk/talk_mid.png": "Talking with medium mouth opening; parrot stays perched; NO pose/framing change.",
        "talk/talk_wide.png": "Talking with wide mouth opening (largest); keep it stylized/readable; parrot LED glow stronger; NO pose/framing change.",

        # read (5)
        "read/read_1.png": "Reading expression (eyes only): look slightly down as if reading; mouth neutral; NO pose/framing change; parrot stays perched.",
        "read/read_2.png": "Reading variant 2 (eyes only): eyes engaged through monocle lens; mouth neutral; NO pose/framing change; parrot stays perched.",
        "read/read_3.png": "Reading variant 3 (face only): relaxed mouth; subtle blink; NO pose/framing change; parrot stays perched.",
        "read/read_4.png": "Reading variant 4 (face only): more serious brow; mouth neutral; NO pose/framing change; parrot stays perched.",
        "read/read_5.png": "Reading variant 5 (face only): ‘aha’ look while still reading; mouth neutral; NO pose/framing change; parrot stays perched.",

        # write (4)
        "write/write_1.png": "Writing variant 1 (face only): focused expression; mouth neutral; parrot stays perched; NO pose/framing change.",
        "write/write_2.png": "Writing variant 2 (face only): subtle brow focus and eye movement; mouth neutral; parrot stays perched; NO pose/framing change.",
        "write/write_3.png": "Writing variant 3 (face only): tighter brow focus; mouth neutral; parrot stays perched; NO pose/framing change.",
        "write/write_4.png": "Writing variant 4 (face only): slight smile of progress; parrot blinks once (no reposition); NO pose/framing change.",

        # tool (4)
        "tool/tool_1.png": "Tool variant 1 (face only): focused expression; mouth neutral; parrot stays perched; NO pose/framing change.",
        "tool/tool_2.png": "Tool variant 2 (face only): different eye/eyebrow expression (generic tool focus); mouth neutral; parrot stays perched; NO pose/framing change.",
        "tool/tool_3.png": "Tool variant 3 (face only): more intense focus; cyber arm glow slightly brighter but arm position unchanged; parrot stays perched; NO pose/framing change.",
        "tool/tool_4.png": "Tool variant 4 (face only): calm focused expression; parrot LED pulse once (no reposition); cyber arm glow baseline; NO pose/framing change.",

        # success (3)
        "success/success_1.png": "Success variant 1 (face only): small celebratory grin; parrot LED warm glow; parrot stays perched; NO pose/framing change.",
        "success/success_2.png": "Success variant 2 (face only): proud grin; parrot stays perched; NO pose/framing change.",
        "success/success_3.png": "Success variant 3 (face only): confident pleased look; parrot LED glow brighter; cyber arm glow brighter but arm position unchanged; NO pose/framing change.",

        # failure (3)
        "failure/failure_1.png": "Failure variant 1 (face only): disappointed expression; mouth slightly down; parrot LED dims; NO pose/framing change; parrot stays perched.",
        "failure/failure_2.png": "Failure variant 2 (face only): ‘uh-oh’ wider eyes; parrot LED flickers lightly; NO pose/framing change; parrot stays perched.",
        "failure/failure_3.png": "Failure variant 3 (face only): sigh expression; mouth neutral/loose; cyber arm glow slightly reduced but arm position unchanged; NO pose/framing change; parrot stays perched.",
    }

    if include_compact:
        manifest.update(
            {
                "compact/compact_1.png": "Compact variant 1 (face only): neutral expression; parrot stays perched; NO pose/framing change.",
                "compact/compact_2.png": "Compact variant 2 (face only): neutral expression; parrot stays perched; NO pose/framing change.",
            }
        )

    return manifest


def main():
    parser = argparse.ArgumentParser(description="Generate pi-emote PNG frames from a master via OpenAI Images API edits.")
    parser.add_argument("--master", default="master_img.png", help="Path to shoulder-up master image (PNG).")
    parser.add_argument("--output", default="emotes/cyber-greymane", help="Output directory for the generated frames.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--size", default=DEFAULT_SIZE, help="Output size passed to images.edit, e.g. 1024x1024")
    parser.add_argument("--quality", default=DEFAULT_QUALITY)
    parser.add_argument("--background", default=DEFAULT_BACKGROUND, choices=["transparent", "opaque", "auto"])
    parser.add_argument("--include-compact", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="Generate only the first N frames (sorted by path) for testing.")

    # Post-processing: background removal when API can't output transparency.
    parser.add_argument("--remove-bg", action="store_true", help="After generating, remove solid background locally via ImageMagick (writes transparent PNGs).")
    parser.add_argument("--remove-bg-only", action="store_true", help="Skip generation; only run local bg removal on existing PNGs under --output.")
    parser.add_argument("--bg-fuzz", type=str, default="8%", help="Fuzz for bg removal, e.g. 5%% or 12%%.")

    args = parser.parse_args()

    master_path = args.master
    if not os.path.isfile(master_path):
        raise SystemExit(f"Missing --master image: {master_path}")

    out_root = args.output
    os.makedirs(out_root, exist_ok=True)

    # If requested, do only local background removal.
    if args.remove_bg_only:
        # Ensure output exists.
        if not os.path.isdir(out_root):
            raise SystemExit(f"Missing --output directory: {out_root}")

        print(f"[info] bg-removal-only: scanning for PNGs under {out_root}")
        for dirpath, _dirnames, filenames in os.walk(out_root):
            for fn in sorted(filenames):
                if not fn.lower().endswith('.png'):
                    continue
                p = os.path.join(dirpath, fn)
                print(f"[post] {os.path.relpath(p, out_root)}")
                remove_background(p, fuzz=args.bg_fuzz)

        print("[done] bg-removal-only complete")
        return

    manifest = build_manifest(include_compact=args.include_compact)
    items = sorted(manifest.items(), key=lambda kv: kv[0])
    if args.limit and args.limit > 0:
        items = items[: args.limit]

    client = OpenAI()

    print(f"[info] master={master_path}")
    print(f"[info] output={out_root}")
    print(f"[info] generating {len(items)} frame(s)")

    # Edit for each output filename.
    for rel_path, change_desc in items:
        out_path = os.path.join(out_root, rel_path)
        if os.path.exists(out_path) and not args.overwrite:
            print(f"[skip] {rel_path} exists (use --overwrite to replace)")
            continue

        edit_prompt = EDIT_PROMPT_TEMPLATE.format(change=change_desc)

        background_mode = args.background

        def do_call(bg: str):
            with open(master_path, "rb") as img_f:
                return client.images.edit(
                    model=args.model,
                    image=img_f,
                    prompt=edit_prompt,
                    size=args.size,
                    quality=args.quality,
                    background=bg,
                    output_format="png",
                )

        print(f"[gen] {rel_path}")

        try:
            resp = call_with_retries(lambda: do_call(background_mode))
        except Exception as e:  # noqa: BLE001
            # Some accounts/models reject transparent background.
            # Detect that specific case and transparently retry with opaque.
            msg = str(e)
            if args.background == "transparent" and (
                "Transparent background is not supported" in msg
                or "transparent background" in msg.lower()
            ):
                print("[warn] transparent unsupported; retrying this frame with background='opaque'")
                resp = call_with_retries(lambda: do_call("opaque"))
            else:
                raise

        b64_json = resp.data[0].b64_json
        save_b64_png(b64_json, out_path)

        if args.remove_bg:
            try:
                remove_background(out_path, fuzz=args.bg_fuzz)
            except Exception as e:  # noqa: BLE001
                # If bg removal fails, keep the opaque frame so the pipeline doesn't block.
                print(f"[warn] bg removal failed for {rel_path}: {e}. Keeping original output.")

    print("[done] generation complete")


if __name__ == "__main__":
    main()
