#!/usr/bin/env python3
"""Generate matching application icons with Pillow (no OS-specific graphic tools)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "generated"
S = 1024

def make_icon():
    canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    base = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(base, "RGBA")
    for y in range(40, 985):
        t = (y - 40) / 944
        draw.line([(40, y), (984, y)], fill=(int(35 - 19*t), int(13 + 2*t), int(70 - 18*t), 255), width=1)
    shape = Image.new("L", (S, S))
    ImageDraw.Draw(shape).rounded_rectangle((40, 40, 984, 984), radius=220, fill=255)
    canvas.paste(base, (0, 0), shape)
    halo = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    h = ImageDraw.Draw(halo, "RGBA")
    h.rounded_rectangle((60, 55, 965, 971), radius=215, outline=(242, 62, 231, 180), width=28)
    h.ellipse((85, 270, 970, 810), outline=(238, 47, 247, 155), width=32)
    h.ellipse((200, 110, 880, 690), fill=(172, 62, 240, 30))
    glow = halo.filter(ImageFilter.GaussianBlur(38))
    canvas = Image.alpha_composite(canvas, glow)
    canvas = Image.alpha_composite(canvas, halo)
    pen = ImageDraw.Draw(canvas, "RGBA")
    # Diagonal avatar tag with a violet rim and a high-contrast lavender face.
    tag = [(157, 695), (321, 363), (612, 251), (770, 276), (884, 406), (841, 709), (693, 888), (334, 831)]
    pen.polygon(tag, fill=(211, 164, 255, 255), outline=(245, 166, 255, 255), width=19)
    pen.line(tag + [tag[0]], fill=(155, 52, 227, 255), width=20, joint="curve")
    pen.line([(181, 690), (333, 378), (616, 282)], fill=(255, 231, 255, 170), width=19, joint="curve")
    # Ring and grommet at the top of the avatar tag.
    pen.ellipse((698, 237, 854, 399), fill=(55, 16, 107, 255), outline=(252, 231, 255, 255), width=24)
    pen.ellipse((729, 268, 824, 365), fill=(29, 9, 68, 255))
    pen.arc((721, 115, 971, 416), start=176, end=352, fill=(225, 168, 255, 255), width=33)
    # Eared avatar silhouette, rather than any actual avatar or third-party logo.
    dark = (45, 14, 90, 255)
    pen.polygon([(302, 508), (334, 389), (439, 452), (540, 408), (593, 482), (595, 639), (337, 677)], fill=dark)
    pen.ellipse((344, 452, 584, 680), fill=dark)
    pen.ellipse((287, 628, 619, 785), fill=dark)
    pen.pieslice((333, 430, 584, 662), start=15, end=170, fill=(108, 34, 164, 255))
    pen.polygon([(360, 518), (435, 460), (452, 571), (496, 482), (518, 600), (570, 536), (561, 470), (422, 427)], fill=(224, 181, 255, 255))
    # Cyan and pink tags.
    pen.rounded_rectangle((624, 524, 815, 596), radius=26, fill=(48, 232, 250, 255), outline=(178, 255, 255, 255), width=6)
    pen.ellipse((643, 544, 669, 570), fill=dark)
    pen.rounded_rectangle((607, 617, 798, 689), radius=26, fill=(252, 67, 181, 255), outline=(255, 180, 232, 255), width=6)
    pen.ellipse((629, 638, 654, 664), fill=dark)
    for cx, cy, r in [(252, 312, 60), (815, 796, 52)]:
        pen.polygon([(cx, cy-r), (cx+int(r*.17), cy-int(r*.17)), (cx+r, cy), (cx+int(r*.17), cy+int(r*.17)), (cx, cy+r), (cx-int(r*.17), cy+int(r*.17)), (cx-r, cy), (cx-int(r*.17), cy-int(r*.17))], fill=(80, 241, 255, 255))
    canvas.putalpha(Image.composite(canvas.getchannel("A"), Image.new("L", (S, S), 0), shape))
    return canvas

def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    image = make_icon()
    image.save(OUTPUT / "app-icon.png", optimize=True)
    image.save(OUTPUT / "app-icon.ico", format="ICO", sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
    image.save(OUTPUT / "app-icon.icns", format="ICNS")
    print(f"Generated macOS, Windows and PNG icons in {OUTPUT}")

if __name__ == "__main__":
    main()
