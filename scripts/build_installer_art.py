#!/usr/bin/env python3
"""Generate branded DMG Finder background and Windows setup wizard images."""
from pathlib import Path
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "generated"
ICON = OUT / "app-icon.png"


def font(size, bold=False):
    choices = (
        ["C:/Windows/Fonts/segoeuib.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "DejaVuSans-Bold.ttf"]
        if bold else
        ["C:/Windows/Fonts/segoeui.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf", "DejaVuSans.ttf"]
    )
    for path in choices:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def backdrop(size):
    w, h = size
    img = Image.new("RGB", size)
    px = img.load()
    for y in range(h):
        for x in range(w):
            dx = x / w - 0.72
            dy = y / h - 0.18
            glow = max(0.0, 1.0 - math.sqrt(dx*dx+dy*dy)*1.9)
            left = max(0.0, 1.0-math.sqrt((x/w-.06)**2+(y/h-.86)**2)*1.9)
            px[x,y] = (
                min(255, int(13+glow*49+left*16)),
                min(255, int(15+glow*22+left*5)),
                min(255, int(34+glow*85+left*47)),
            )
    return img


def draw_centered(draw, xy, text, text_font, color, anchor="mm"):
    draw.text(xy, text, font=text_font, fill=color, anchor=anchor)


def draw_dmg():
    image = backdrop((720, 460)).convert("RGBA")
    d = ImageDraw.Draw(image)
    d.rounded_rectangle((15, 15, 705, 445), radius=28, outline=(174, 118, 250, 170), width=2)
    d.text((43, 40), "AVATAR TAGGER", font=font(17, True), fill=(248, 239, 255, 255))
    d.text((43, 70), "THE CREATOR'S DESKTOP WORKSPACE", font=font(12, True), fill=(166, 143, 225, 255))
    draw_centered(d, (360, 148), "DRAG TO INSTALL", font(25, True), (253, 241, 255, 255))
    d.line([(340, 244), (388, 244)], fill=(224, 163, 255, 255), width=6)
    d.polygon([(388, 231), (412, 244), (388, 258)], fill=(224, 163, 255, 255))
    d.rounded_rectangle((68, 176, 285, 331), radius=22, outline=(194, 123, 251, 100), width=2)
    d.rounded_rectangle((432, 176, 649, 331), radius=22, outline=(91, 228, 252, 110), width=2)
    draw_centered(d, (360, 382), "Move the app to Applications, then launch it.", font(15), (211, 203, 236, 255))
    draw_centered(d, (360, 416), "macOS · Apple Silicon & Intel", font(12), (157, 150, 189, 255))
    image.convert("RGB").save(OUT / "installer-dmg-bg.png", optimize=True)


def draw_windows():
    image = backdrop((480, 920)).convert("RGBA")
    d = ImageDraw.Draw(image)
    d.rounded_rectangle((17, 17, 463, 903), radius=40, outline=(172, 105, 242, 150), width=3)
    d.ellipse((-160, 430, 330, 950), outline=(236, 63, 216, 110), width=17)
    icon = Image.open(ICON).convert("RGBA").resize((268, 268), Image.Resampling.LANCZOS)
    image.alpha_composite(icon, (105, 135))
    d = ImageDraw.Draw(image)
    draw_centered(d, (240, 480), "VRCHAT", font(38, True), (255, 241, 255, 255))
    draw_centered(d, (240, 535), "AVATAR TAGGER", font(29, True), (255, 241, 255, 255))
    draw_centered(d, (240, 609), "YOUR AVATARS.", font(20, True), (126, 226, 251, 255))
    draw_centered(d, (240, 647), "YOUR TAGS.", font(20, True), (255, 144, 219, 255))
    draw_centered(d, (240, 741), "Manage your collection", font(18), (212, 204, 235, 255))
    draw_centered(d, (240, 772), "with fewer clicks.", font(18), (212, 204, 235, 255))
    draw_centered(d, (240, 856), "FREE  •  OPEN SOURCE", font(13, True), (175, 158, 210, 255))
    image.save(OUT / "installer-wizard.png", optimize=True)
    image.resize((240, 460), Image.Resampling.LANCZOS).save(OUT / "installer-wizard-small.png", optimize=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if not ICON.exists():
        raise FileNotFoundError("Build icons first: python scripts/build_icons.py")
    draw_dmg()
    draw_windows()
    print("Generated custom DMG and Windows installer artwork.")


if __name__ == "__main__":
    main()
