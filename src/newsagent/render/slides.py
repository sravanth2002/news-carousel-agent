from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from newsagent.images import get_image
from newsagent.models import Slide

W, H = 1080, 1350
FONT = "/System/Library/Fonts/Helvetica.ttc"
WHITE, RED, INK, GREY = (255, 255, 255), (200, 16, 46), (20, 20, 25), (85, 90, 100)
GREEN = (20, 130, 60)
BORDER, MARGIN = 28, 100
IMG_W, IMG_H = W - 2 * MARGIN, 440
COLS = [0, 200, 380, 560, 740]


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(FONT, size, index=1 if bold else 0)
    except OSError:
        return ImageFont.load_default(size)


def _wrap(d: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        t = f"{cur} {word}".strip()
        if d.textlength(t, font=font) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = word
    return lines + [cur]


def _table(d: ImageDraw.ImageDraw, rows: list[list[str]], y: int) -> None:
    for r, row in enumerate(rows):
        for x, cell in zip(COLS, row):
            if r == 0:
                col = GREY
            elif x == COLS[-1]:
                col = GREEN if cell.startswith("+") else RED if cell.startswith("-") else GREY
            else:
                col = INK
            d.text((MARGIN + x, y), cell, font=_font(30, r == 0 or x == 0), fill=col)
        y += 62
        if r == 0:
            d.line((MARGIN, y - 10, W - MARGIN, y - 10), fill=RED, width=3)


def render_slides(slides: list[Slide], out_dir: str) -> list[Path]:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    paths = []
    text_w = W - 2 * MARGIN
    for i, s in enumerate(slides, 1):
        img = Image.new("RGB", (W, H), WHITE)
        d = ImageDraw.Draw(img)
        d.rectangle((0, 0, W - 1, H - 1), outline=RED, width=BORDER)
        d.text(
            (MARGIN, 70),
            f"{i:02d} / {len(slides):02d}  |  {s.category}",
            font=_font(34, True),
            fill=RED,
        )

        photo, credit_suffix = get_image(s, i)
        if photo:
            img.paste(ImageOps.fit(photo, (IMG_W, IMG_H)), (MARGIN, 125))
            d.rectangle((MARGIN, 125 + IMG_H, MARGIN + IMG_W, 125 + IMG_H + 8), fill=RED)
            y, hsize, bsize, max_body = 125 + IMG_H + 50, 60, 38, 5
        else:
            y, hsize, bsize, max_body = 240, 72, 44, 8

        hf = _font(hsize, True)
        for line in _wrap(d, s.headline, hf, text_w):
            d.text((MARGIN, y), line, font=hf, fill=INK)
            y += int(hsize * 1.27)

        y += 20
        d.rectangle((MARGIN, y, MARGIN + 160, y + 10), fill=RED)
        y += 50

        if s.rows:
            _table(d, s.rows, y)
        else:
            bf = _font(bsize)
            for line in _wrap(d, s.body, bf, text_w)[:max_body]:
                d.text((MARGIN, y), line, font=bf, fill=GREY)
                y += int(bsize * 1.45)

        d.text(
            (MARGIN, H - 120),
            f"Source: {s.source}{credit_suffix if photo else ''}",
            font=_font(28),
            fill=GREY,
        )
        if i < len(slides):
            d.text((W - MARGIN - 140, H - 120), "Swipe >", font=_font(32, True), fill=RED)

        p = Path(out_dir) / f"slide_{i:02d}.jpg"
        img.save(p, quality=95)
        paths.append(p)
    return paths
