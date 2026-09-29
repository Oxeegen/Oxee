#!/usr/bin/env python3
"""Regenerate every Oxee icon from the Oxee mark.

The mark is a disc cut by two vertical gaps into three bands, measured from
the 64 px mark Oxeegen uses in its other apps. Every upstream image is
replaced at its own size and in its own role, so the file list never needs
maintaining by hand:

  * app icons (iOS AppIcon sets, Android legacy launcher): white mark on the
    Oxee purple gradient; iOS icons are opaque, as App Store requires;
  * Android adaptive layers: gradient background, white or monochrome mark
    inside the 66 dp safe zone;
  * splash / launch images and assets/icons/icon.png: rounded icon on
    transparency;
  * the widget and notification glyph (vector): the mark alone.

The debug build gets a graphite background so both can sit side by side.

    python brand/tools/make_icons.py

Requires Pillow. The geometry is in one place (GAP_1, GAP_2); when Oxeegen
supplies official artwork, draw from it here instead.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]

# Horizontal bands across the disc's diameter, as fractions of it:
# solid, gap, solid (middle bar), gap, solid.
GAP_1 = (0.297, 0.4375)
GAP_2 = (0.5625, 0.703)

PURPLE = ((0x6E, 0x2F, 0xFF), (0x47, 0x03, 0xE8))   # top-left -> bottom-right
GRAPHITE = ((0x4B, 0x50, 0x5C), (0x22, 0x25, 0x2C))  # debug builds
SS = 4  # supersampling factor


def gradient(size: int, colors) -> Image.Image:
    (r0, g0, b0), (r1, g1, b1) = colors
    small = 256
    grad = Image.new("RGB", (small, small))
    px = grad.load()
    for y in range(small):
        for x in range(small):
            t = (x + y) / (2 * (small - 1))
            px[x, y] = (round(r0 + (r1 - r0) * t), round(g0 + (g1 - g0) * t), round(b0 + (b1 - b0) * t))
    return grad.resize((size, size), Image.BICUBIC)


def mark_mask(size: int, diameter: float) -> Image.Image:
    """L-mode mask of the mark centred in a size x size canvas."""
    big = size * SS
    d = diameter * SS
    off = (big - d) / 2
    mask = Image.new("L", (big, big), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((off, off, off + d, off + d), fill=255)
    for lo, hi in (GAP_1, GAP_2):
        draw.rectangle((off + lo * d, 0, off + hi * d, big), fill=0)
    return mask.resize((size, size), Image.LANCZOS)


def rounded_mask(size: int, radius_frac: float = 0.2237) -> Image.Image:
    big = size * SS
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, big - 1, big - 1), radius=big * radius_frac, fill=255)
    return mask.resize((size, size), Image.LANCZOS)


def app_icon(size: int, colors, opaque: bool) -> Image.Image:
    """White mark on the gradient, full square (the OS applies its own mask)."""
    base = gradient(size, colors).convert("RGBA")
    white = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    base.paste(white, (0, 0), mark_mask(size, size * 0.60))
    return base.convert("RGB") if opaque else base


def rounded_icon(size: int, colors) -> Image.Image:
    icon = app_icon(size, colors, opaque=False)
    icon.putalpha(rounded_mask(size))
    return icon


def adaptive_foreground(size: int, color=(255, 255, 255)) -> Image.Image:
    # 108 dp canvas, 66 dp safe circle: a 48% mark keeps clear of every mask.
    layer = Image.new("RGBA", (size, size), color + (0,))
    layer.putalpha(mark_mask(size, size * 0.48))
    return layer


def replace(path: Path, image: Image.Image) -> None:
    before = Image.open(path)
    if before.size != image.size:
        raise SystemExit(f"{path}: size {image.size} != {before.size}")
    image.save(path, optimize=True)


# ---------------------------------------------------------------------------
# Vector glyph (Android vector drawable, iOS widget template image)
# ---------------------------------------------------------------------------


def glyph_paths(center: float, radius: float) -> list[str]:
    def chord(x: float) -> tuple[float, float]:
        h = (radius ** 2 - (x - center) ** 2) ** 0.5
        return center - h, center + h

    d = 2 * radius
    left = center - radius
    x1, x2 = left + GAP_1[0] * d, left + GAP_1[1] * d
    x3, x4 = left + GAP_2[0] * d, left + GAP_2[1] * d
    f = lambda v: f"{v:.3f}".rstrip("0").rstrip(".")
    t1, b1 = chord(x1)
    t2, b2 = chord(x2)
    t3, b3 = chord(x3)
    t4, b4 = chord(x4)
    r = f(radius)
    return [
        # Left band: chord at x1, round side on the left.
        f"M{f(x1)},{f(t1)} A{r},{r} 0 0,0 {f(x1)},{f(b1)} Z",
        # Middle bar between x2 and x3, round top and bottom.
        f"M{f(x2)},{f(t2)} A{r},{r} 0 0,1 {f(x3)},{f(t3)} L{f(x3)},{f(b3)} A{r},{r} 0 0,1 {f(x2)},{f(b2)} Z",
        # Right band: chord at x4, round side on the right.
        f"M{f(x4)},{f(t4)} A{r},{r} 0 0,1 {f(x4)},{f(b4)} Z",
    ]


def write_vectors() -> None:
    paths = glyph_paths(12, 10)
    android = ROOT / "android/app/src/main/res/drawable/ic_hub.xml"
    body = "\n".join(
        f'    <path\n        android:fillColor="@android:color/white"\n        android:pathData="{p}" />'
        for p in paths
    )
    android.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<!-- Oxee mark (brand/tools/make_icons.py). Widget and notification glyph. -->\n"
        '<vector xmlns:android="http://schemas.android.com/apk/res/android"\n'
        '    android:width="24dp"\n    android:height="24dp"\n'
        '    android:viewportWidth="24"\n    android:viewportHeight="24"\n'
        '    android:tint="#FFFFFF">\n' + body + "\n</vector>\n",
        encoding="utf-8",
    )
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">'
        + "".join(f'<path d="{p}"/>' for p in paths)
        + "</svg>\n"
    )
    (ROOT / "ios/ConduitWidget/Assets.xcassets/HubIcon.imageset/hub.svg").write_text(svg, encoding="utf-8")
    master = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">'
        '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="#{"%02X%02X%02X" % PURPLE[0]}"/>'
        f'<stop offset="1" stop-color="#{"%02X%02X%02X" % PURPLE[1]}"/></linearGradient></defs>'
        + "".join(f'<path fill="url(#g)" d="{p}"/>' for p in glyph_paths(512, 512))
        + "</svg>\n"
    )
    (ROOT / "brand/assets/oxee-mark.svg").write_text(master, encoding="utf-8")


def main() -> None:
    (ROOT / "brand/assets").mkdir(parents=True, exist_ok=True)
    app_icon(1024, PURPLE, opaque=True).save(ROOT / "brand/assets/oxee-icon-1024.png", optimize=True)
    mark = gradient(1024, PURPLE).convert("RGBA")
    mark.putalpha(mark_mask(1024, 1024))
    mark.save(ROOT / "brand/assets/oxee-mark-1024.png", optimize=True)

    count = 0
    for set_dir, colors in (("AppIcon.appiconset", PURPLE), ("AppIcon-Debug.appiconset", GRAPHITE)):
        for png in sorted((ROOT / "ios/Runner/Assets.xcassets" / set_dir).glob("*.png")):
            replace(png, app_icon(Image.open(png).size[0], colors, opaque=True))
            count += 1

    for png in sorted((ROOT / "ios/Runner/Assets.xcassets/LaunchImage.imageset").glob("*.png")):
        replace(png, rounded_icon(Image.open(png).size[0], PURPLE))
        count += 1

    for variant, colors in (("main", PURPLE), ("debug", GRAPHITE)):
        for mip in sorted((ROOT / f"android/app/src/{variant}/res").glob("mipmap-*")):
            for png in sorted(mip.glob("*.png")):
                size = Image.open(png).size[0]
                name = png.stem
                if name == "ic_launcher":
                    image = rounded_icon(size, colors)
                elif name == "ic_launcher_background":
                    image = gradient(size, colors).convert("RGBA")
                elif name == "ic_launcher_foreground":
                    image = adaptive_foreground(size)
                elif name == "ic_launcher_monochrome":
                    image = adaptive_foreground(size, (0, 0, 0))
                else:
                    raise SystemExit(f"unknown launcher layer {png}")
                replace(png, image)
                count += 1

    for png in sorted((ROOT / "android/app/src/main/res").glob("drawable-*/splash.png")):
        replace(png, rounded_icon(Image.open(png).size[0], PURPLE))
        count += 1

    replace(ROOT / "assets/icons/icon.png", rounded_icon(512, PURPLE))
    count += 1

    write_vectors()
    print(f"make_icons: {count} raster icons regenerated, vectors written")


if __name__ == "__main__":
    main()
