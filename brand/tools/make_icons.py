#!/usr/bin/env python3
"""Regenerate every Oxee icon from the official Oxee mark.

Source: brand/assets/oxee-mark-master.png (1120 px, transparent), the mark
Oxeegen uses in its other apps. Every upstream image is replaced at its own
size and in its own role, so the file list never needs maintaining by hand:

  * app icons (iOS AppIcon sets, Android legacy launcher): the purple mark on
    white, filling MARK_SHARE of the icon (Claude's logo fills 65% of its
    icon, ChatGPT's 81%, measured on an iPhone home screen); iOS icons are
    opaque, as the App Store requires;
  * Android adaptive layers: white background, the mark (or its monochrome
    silhouette) sized so it matches the iOS proportion inside the visible
    72 dp of the 108 dp canvas;
  * splash / launch images and assets/icons/icon.png: the mark alone on
    transparency;
  * the widget and notification glyph (vector): the mark's shape, one colour.

The debug build gets a light grey background so both can sit side by side.

    python brand/tools/make_icons.py

Requires Pillow.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / "brand/assets/oxee-mark-master.png"

MARK_SHARE = 0.73                 # mark width / icon width
WHITE = (255, 255, 255)
DEBUG_GREY = (0xE6, 0xE6, 0xEC)
# Cuts across the mark, as fractions of its width (measured on the master):
# left segment, gap, middle bar (full height), gap, right segment.
GAP_1 = (0.298, 0.432)
GAP_2 = (0.568, 0.701)
GLYPH_COLOURS = ((0x5C, 0x1B, 0xFF), (0x42, 0x00, 0xEA))  # master, top -> bottom
SS = 4  # supersampling for masks


def master() -> Image.Image:
    im = Image.open(MASTER).convert("RGBA")
    return im.crop(im.getbbox())


MARK = None


def mark(width: int) -> Image.Image:
    global MARK
    if MARK is None:
        MARK = master()
    height = round(MARK.height * width / MARK.width)
    return MARK.resize((width, height), Image.LANCZOS)


def on_canvas(size: int, share: float, background=None) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), (background or WHITE) + ((255,) if background else (0,)))
    m = mark(max(1, round(size * share)))
    canvas.alpha_composite(m, ((size - m.width) // 2, (size - m.height) // 2))
    return canvas


def app_icon(size: int, background=WHITE) -> Image.Image:
    """Full square; the OS applies its own mask. Opaque for the App Store."""
    return on_canvas(size, MARK_SHARE, background).convert("RGB")


def rounded_mask(size: int, radius_frac: float = 0.2237) -> Image.Image:
    big = size * SS
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, big - 1, big - 1), radius=big * radius_frac, fill=255)
    return mask.resize((size, size), Image.LANCZOS)


def rounded_icon(size: int, background=WHITE) -> Image.Image:
    icon = on_canvas(size, MARK_SHARE, background)
    icon.putalpha(rounded_mask(size))
    return icon


# Adaptive icons show the middle 72 dp of a 108 dp layer.
ADAPTIVE_SHARE = MARK_SHARE * 72 / 108


def adaptive_foreground(size: int) -> Image.Image:
    return on_canvas(size, ADAPTIVE_SHARE)


def adaptive_monochrome(size: int) -> Image.Image:
    layer = on_canvas(size, ADAPTIVE_SHARE)
    silhouette = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    silhouette.putalpha(layer.getchannel("A"))
    return silhouette


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
    top, bottom = center - radius, center + radius
    x1, x2 = left + GAP_1[0] * d, left + GAP_1[1] * d
    x3, x4 = left + GAP_2[0] * d, left + GAP_2[1] * d
    f = lambda v: f"{v:.3f}".rstrip("0").rstrip(".")
    t1, b1 = chord(x1)
    t4, b4 = chord(x4)
    r = f(radius)
    return [
        # Left segment: chord at x1, round side on the left.
        f"M{f(x1)},{f(t1)} A{r},{r} 0 0,0 {f(x1)},{f(b1)} Z",
        # Middle bar: the full height of the mark.
        f"M{f(x2)},{f(top)} L{f(x3)},{f(top)} L{f(x3)},{f(bottom)} L{f(x2)},{f(bottom)} Z",
        # Right segment: chord at x4, round side on the right.
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
    top, bottom = ("#%02X%02X%02X" % c for c in GLYPH_COLOURS)
    vector = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">'
        '<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{top}"/><stop offset="1" stop-color="{bottom}"/>'
        "</linearGradient></defs>"
        + "".join(f'<path fill="url(#g)" d="{p}"/>' for p in glyph_paths(512, 512))
        + "</svg>\n"
    )
    (ROOT / "brand/assets/oxee-mark.svg").write_text(vector, encoding="utf-8")


def main() -> None:
    assets = ROOT / "brand/assets"
    app_icon(1024).save(assets / "oxee-icon-1024.png", optimize=True)
    on_canvas(1024, 1.0).save(assets / "oxee-mark-1024.png", optimize=True)

    count = 0
    for set_dir, background in (("AppIcon.appiconset", WHITE), ("AppIcon-Debug.appiconset", DEBUG_GREY)):
        for png in sorted((ROOT / "ios/Runner/Assets.xcassets" / set_dir).glob("*.png")):
            replace(png, app_icon(Image.open(png).size[0], background))
            count += 1

    for png in sorted((ROOT / "ios/Runner/Assets.xcassets/LaunchImage.imageset").glob("*.png")):
        replace(png, on_canvas(Image.open(png).size[0], 0.8))
        count += 1

    for variant, background in (("main", WHITE), ("debug", DEBUG_GREY)):
        for mip in sorted((ROOT / f"android/app/src/{variant}/res").glob("mipmap-*")):
            for png in sorted(mip.glob("*.png")):
                size = Image.open(png).size[0]
                layer = {
                    "ic_launcher": lambda: rounded_icon(size, background),
                    "ic_launcher_background": lambda: Image.new("RGBA", (size, size), background + (255,)),
                    "ic_launcher_foreground": lambda: adaptive_foreground(size),
                    "ic_launcher_monochrome": lambda: adaptive_monochrome(size),
                }.get(png.stem)
                if layer is None:
                    raise SystemExit(f"unknown launcher layer {png}")
                replace(png, layer())
                count += 1

    for png in sorted((ROOT / "android/app/src/main/res").glob("drawable-*/splash.png")):
        replace(png, on_canvas(Image.open(png).size[0], 0.8))
        count += 1

    replace(ROOT / "assets/icons/icon.png", on_canvas(512, 0.8))
    count += 1

    write_vectors()
    print(f"make_icons: {count} raster icons regenerated from {MASTER.name}, vectors written")


if __name__ == "__main__":
    main()
