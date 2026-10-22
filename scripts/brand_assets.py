"""Trace the existing transparent glasses mark and generate application icon assets."""

from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1] / "openduet/web/brand"


def main():
    source = Image.open(ROOT / "source-mark.png").convert("RGBA")
    alpha = source.getchannel("A")
    width, height = source.size
    pixels = alpha.load()
    edges = defaultdict(list)
    for y in range(height):
        for x in range(width):
            if pixels[x, y] < 128:
                continue
            if y == 0 or pixels[x, y - 1] < 128:
                edges[(x, y)].append((x + 1, y))
            if x == width - 1 or pixels[x + 1, y] < 128:
                edges[(x + 1, y)].append((x + 1, y + 1))
            if y == height - 1 or pixels[x, y + 1] < 128:
                edges[(x + 1, y + 1)].append((x, y + 1))
            if x == 0 or pixels[x - 1, y] < 128:
                edges[(x, y + 1)].append((x, y))
    paths = []
    while edges:
        start = next(iter(edges))
        point, points = start, [start]
        while point in edges:
            following = edges[point].pop()
            if not edges[point]:
                del edges[point]
            point = following
            points.append(point)
            if point == start:
                break
        reduced = [points[0]]
        for a, b, c in zip(points, points[1:], points[2:]):
            if (b[0] - a[0]) * (c[1] - b[1]) != (b[1] - a[1]) * (c[0] - b[0]):
                reduced.append(b)
        if len(reduced) < 3:
            continue
        paths.append("M" + " L".join(f"{x} {y}" for x, y in reduced) + " Z")
    markup = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" fill="currentColor"><g id="mark"><path fill-rule="evenodd" d="'
        + " ".join(paths)
        + '"/></g></svg>'
    )
    (ROOT / "mark.svg").write_text(markup + "\n")
    (ROOT / "mark.js").write_text("export const glasses = " + repr(markup) + ";\n")
    for name, size in (
        ("favicon.png", 32),
        ("apple-touch-icon.png", 180),
        ("icon-192.png", 192),
        ("icon-512.png", 512),
        ("maskable-512.png", 512),
        ("telegram-avatar.png", 512),
    ):
        canvas = Image.new("RGBA", (size, size), "#f5f3ed")
        mark = source.copy()
        mark.thumbnail((int(size * 0.8), int(size * 0.55)), Image.Resampling.LANCZOS)
        canvas.alpha_composite(mark, ((size - mark.width) // 2, (size - mark.height) // 2))
        canvas.convert("RGB").save(ROOT / name)
    canvas = Image.new("RGB", (1200, 630), "#f5f3ed")
    mark = source.copy()
    mark.thumbnail((420, 220), Image.Resampling.LANCZOS)
    canvas.paste(mark, ((1200 - mark.width) // 2, 90), mark)
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 68)
    except OSError:
        font = ImageFont.load_default(size=68)
    draw.text((600, 390), "OpenDuet", font=font, fill="#292e27", anchor="mm")
    draw.text(
        (600, 485),
        "Your work. Your models.",
        font=ImageFont.load_default(size=28),
        fill="#56623f",
        anchor="mm",
    )
    canvas.save(ROOT / "social-preview.png")


if __name__ == "__main__":
    main()
