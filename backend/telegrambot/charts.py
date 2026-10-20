"""
The "Up or down?" charts the bot sends as photos.

Two pictures per round. The question shows the price up to the moment of the
call and a shaded "?" where the future goes; it is scaled on the past alone,
because a range stretched to fit what happens next would give the answer
away. The reveal draws the rest of the story on a shared scale — green if it
went up, red if it went down — with the final price and the change.

Only Latin, digits and symbols on the image: the built-in font has no
Cyrillic, and the words belong in the caption anyway, where they are
translated and can be read by a screen reader.
"""
import io

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 720
SCALE = 2  # drawn at double size and scaled down, for smooth lines
PAST_SHARE = 0.62  # how much of the width the known part takes

BG_TOP = (14, 21, 40)
BG_BOTTOM = (19, 28, 52)
INK = (236, 240, 250)
MUTED = (140, 152, 184)
LINE = (120, 170, 255)
UP = (34, 197, 94)
DOWN = (239, 68, 68)
BRAND = (79, 140, 255)

PAD_L, PAD_R, TOP, BOTTOM = 64, 64, 150, 640


def _font(size):
    return ImageFont.load_default(size=size * SCALE)


def price(value, unit=""):
    """1234.5 -> 1 234.5; drops decimals once a price is big enough not to need them."""
    sign = "-" if value < 0 else ""  # the built-in font has no U+2212
    value = abs(value)
    text = f"{value:,.0f}" if value >= 100 else f"{value:,.2f}".rstrip("0").rstrip(".")
    return f"{sign}{unit}{text.replace(',', ' ')}"


def change(start, end):
    if start <= 0 or end <= 0:
        return ""  # a percentage across zero means nothing; the prices say it
    pct = 100 * (end - start) / start
    return f"{'+' if pct >= 0 else '-'}{abs(pct):.0f}%"


def _canvas():
    image = Image.new("RGB", (W * SCALE, H * SCALE), BG_TOP)
    draw = ImageDraw.Draw(image)
    for y in range(H * SCALE):  # a quiet vertical wash
        t = y / (H * SCALE)
        draw.line([(0, y), (W * SCALE, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOTTOM)))
    return image


def _overlay(image, paint):
    """
    Translucent shapes go on their own layer and are composited: drawn
    straight onto an RGBA image, Pillow writes their alpha into the pixels
    instead of blending, and the PNG comes out with holes in it.
    """
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    paint(ImageDraw.Draw(layer))
    return Image.alpha_composite(image, layer)


def _grid(image):
    def paint(draw):
        for i in range(5):
            y = (TOP + (BOTTOM - TOP) * i / 4) * SCALE
            draw.line([(PAD_L * SCALE, y), ((W - PAD_R) * SCALE, y)], fill=(255, 255, 255, 22), width=SCALE)

    return _overlay(image, paint)


def _points(values, x0, x1, low, high):
    span = (high - low) or 1
    n = max(1, len(values) - 1)
    return [
        ((x0 + (x1 - x0) * i / n) * SCALE, (BOTTOM - (BOTTOM - TOP) * (v - low) / span) * SCALE)
        for i, v in enumerate(values)
    ]


def _glow_line(image, points, color, width=6):
    """The line, with a soft halo in its own colour underneath."""
    halo = Image.new("RGBA", image.size, (0, 0, 0, 0))
    ImageDraw.Draw(halo).line(points, fill=color + (110,), width=width * 3 * SCALE, joint="curve")
    image.alpha_composite(halo.filter(ImageFilter.GaussianBlur(8 * SCALE)))
    ImageDraw.Draw(image).line(points, fill=color, width=width * SCALE, joint="curve")


def _dot(draw, point, color, radius=9):
    x, y = point
    r = radius * SCALE
    draw.ellipse([x - r - 4 * SCALE, y - r - 4 * SCALE, x + r + 4 * SCALE, y + r + 4 * SCALE], fill=BG_BOTTOM)
    draw.ellipse([x - r, y - r, x + r, y + r], fill=color)


def _header(draw, asset):
    draw.text((PAD_L * SCALE, 52 * SCALE), asset, font=_font(46), fill=INK)
    draw.text(((W - PAD_R) * SCALE, 60 * SCALE), "zinvest", font=_font(30), fill=BRAND, anchor="ra")


def _label(draw, point, text, color, above=True, side="m"):
    """`side` is which way the text runs from the point: l(eft edge), m(iddle), r(ight edge)."""
    x, y = point
    offset = -26 if above else 26
    draw.text((x, y + offset * SCALE), text, font=_font(28), fill=color, anchor=side + ("d" if above else "a"))


def _png(image):
    out = io.BytesIO()
    image.convert("RGB").resize((W, H), Image.LANCZOS).save(out, "PNG", optimize=True)
    return out.getvalue()


def question(asset, before, unit=""):
    """The past, the moment of the call, and a shaded question mark."""
    image = _grid(_canvas().convert("RGBA"))
    _header(ImageDraw.Draw(image), asset)

    low, high = min(before), max(before)
    pad = (high - low) * 0.18 or abs(high) * 0.1 or 1
    split = PAD_L + (W - PAD_L - PAD_R) * PAST_SHARE
    points = _points(before, PAD_L, split, low - pad, high + pad)

    # The future: a shaded panel with the question in it.
    def future(draw):
        draw.rounded_rectangle(
            [(split + 22) * SCALE, TOP * SCALE, (W - PAD_R) * SCALE, BOTTOM * SCALE],
            radius=24 * SCALE, fill=(255, 255, 255, 16), outline=(255, 255, 255, 46), width=2 * SCALE,
        )
        draw.text((((split + 22) + (W - PAD_R)) / 2 * SCALE, (TOP + BOTTOM) / 2 * SCALE), "?",
                  font=_font(150), fill=(255, 255, 255, 150), anchor="mm")

    image = _overlay(image, future)
    _glow_line(image, points, LINE)
    draw = ImageDraw.Draw(image)
    _label(draw, points[0], price(before[0], unit), MUTED, above=before[0] >= before[len(before) // 2], side="l")
    _dot(draw, points[-1], INK)
    _label(draw, points[-1], price(before[-1], unit), INK, above=True, side="r")
    return _png(image)


def reveal(asset, before, after, unit="", went_up=True):
    """The whole story on one scale, the new part in green or red."""
    image = _grid(_canvas().convert("RGBA"))
    _header(ImageDraw.Draw(image), asset)

    everything = list(before) + list(after)
    low, high = min(everything), max(everything)
    pad = (high - low) * 0.14 or abs(high) * 0.1 or 1
    split = PAD_L + (W - PAD_L - PAD_R) * PAST_SHARE
    past = _points(before, PAD_L, split, low - pad, high + pad)
    future = _points([before[-1], *after], split, W - PAD_R, low - pad, high + pad)

    if low < 0 < high:  # a price below zero: draw the zero line so it reads as zero
        zero_y = (BOTTOM - (BOTTOM - TOP) * (0 - (low - pad)) / ((high + pad) - (low - pad))) * SCALE

        def zero(draw):
            draw.line([(PAD_L * SCALE, zero_y), ((W - PAD_R) * SCALE, zero_y)], fill=(255, 255, 255, 90), width=2 * SCALE)

        image = _overlay(image, zero)
        ImageDraw.Draw(image).text((PAD_L * SCALE, zero_y - 8 * SCALE), "0", font=_font(24), fill=MUTED, anchor="ld")

    color = UP if went_up else DOWN
    _glow_line(image, past, LINE)
    _glow_line(image, future, color)
    draw = ImageDraw.Draw(image)
    _dot(draw, past[-1], INK, radius=7)
    _label(draw, past[-1], price(before[-1], unit), MUTED, above=not went_up, side="r")
    _dot(draw, future[-1], color)
    end_text = price(after[-1], unit)
    delta = change(before[-1], after[-1])
    _label(draw, future[-1], f"{end_text}  {delta}".strip(), color, above=went_up, side="r")
    return _png(image)
