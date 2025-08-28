import sys
from pathlib import Path
from PIL import Image, ImageSequence

"""
Usage:
  python optimize_gif.py <input.gif> [--max-width 480] [--max-height 480] [--colors 128] [--fps 12] [--lossy 20]

- Resizes preserving aspect ratio (constraining by max width/height)
- Reduces frame rate
- Converts to a global palette with limited colors
- Attempts to use disposal and optimize flags

Outputs a new file alongside input: <stem>.optimized.gif
"""

def optimize_gif(
    input_path: Path,
    max_width: int = 480,
    max_height: int = 480,
    colors: int = 128,
    fps: int = 12,
):
    im = Image.open(input_path)

    # Calculate scale
    w, h = im.size
    scale = min(max_width / w, max_height / h, 1.0)
    new_size = (max(1, int(w * scale)), max(1, int(h * scale)))

    # Determine new duration per frame based on target fps
    # In GIF, duration is in ms per frame.
    orig_durations = [frame.info.get("duration", 100) for frame in ImageSequence.Iterator(im)]
    # Compute an average original fps; if missing, assume 10 fps
    avg_duration = sum(orig_durations) / len(orig_durations) if orig_durations else 100
    target_frame_duration = max(10, int(1000 / fps))

    frames = []
    durations = []

    for i, frame in enumerate(ImageSequence.Iterator(im)):
        frame = frame.convert("RGBA")
        # Downsample frames by skipping according to ratio of durations
        # Keep frames so that resulting duration roughly equals target_frame_duration
        # We'll accumulate time and only append when threshold is met.
        if i == 0:
            acc = 0
        dur = frame.info.get("duration", int(avg_duration))
        acc = locals().get("acc", 0) + dur
        if acc >= target_frame_duration or i == 0:
            acc = 0
            # Resize
            if frame.size != new_size:
                frame = frame.resize(new_size, Image.Resampling.LANCZOS)
            frames.append(frame)
            durations.append(target_frame_duration)

    if not frames:
        # Fallback: at least one frame
        im0 = im.convert("RGBA")
        if im0.size != new_size:
            im0 = im0.resize(new_size, Image.Resampling.LANCZOS)
        frames = [im0]
        durations = [target_frame_duration]

    # Convert to a single global palette to improve compression
    paletted = []
    for f in frames:
        paletted.append(
            f.convert("P", palette=Image.Palette.ADAPTIVE, colors=colors, dither=Image.Dither.FLOYDSTEINBERG)
        )

    out_path = input_path.with_name(input_path.stem + ".optimized.gif")

    # Save optimized GIF
    paletted[0].save(
        out_path,
        save_all=True,
        append_images=paletted[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=2,
        transparency=0,
    )

    return out_path


def main():
    if len(sys.argv) < 2:
        print("Usage: python optimize_gif.py <input.gif> [--max-width 480] [--max-height 480] [--colors 128] [--fps 12]")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"Input not found: {input_path}")
        sys.exit(2)

    # Defaults
    max_width = 480
    max_height = 480
    colors = 128
    fps = 12

    # Parse simple flags
    args = sys.argv[2:]
    def get_flag(name, default):
        if name in args:
            idx = args.index(name)
            try:
                return int(args[idx + 1])
            except Exception:
                return default
        return default

    max_width = get_flag("--max-width", max_width)
    max_height = get_flag("--max-height", max_height)
    colors = get_flag("--colors", colors)
    fps = get_flag("--fps", fps)

    out = optimize_gif(input_path, max_width, max_height, colors, fps)
    print(out)


if __name__ == "__main__":
    main()
