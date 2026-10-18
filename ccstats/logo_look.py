"""How a logo is drawn on the dark pages.

Logos are made for the game's white page, so on a dark page some parts can vanish. Each logo has a look, picked by
comparing it with the original (see STYLES in ccstats/logos.py); a logo with no look picked is shown as it is:

    plain   as it is.
    inside  everything inside the logo's outline sits on white, as on the game's page (a see-through gap or a half
            see-through letter shows white); the page round it stays dark.
    whole   white behind the whole logo, its parts joined up (for a logo drawn half see-through all over).
    line    a thin, soft light line round the logo's edges.
    C       dark parts made visible: dark writing and outlines in a light tint of their own colour; big dark areas
            (a black flag stripe) keep their colour and get a thin light line where they meet the page.
    D       C, plus the white the logo closes in (a ring's middle, a flag's stripes) shown white as in the game.

Every look is drawn in the same square frame for a size, so logos side by side line up."""

from __future__ import annotations

import base64
import io
import math
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

PAGE = np.array([10, 19, 34], float)        # the dark page
LINE = np.array([0xb9, 0xc4, 0xd6], float)  # the soft light line
STYLES = ("plain", "inside", "whole", "line", "C", "D")


def shape(path: str):
    """The logo cut to its visible part."""
    im = Image.open(path).convert("RGBA")
    box = im.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    return im.crop(box) if box else im


def _mask_img(m) -> Image.Image:
    return Image.fromarray((np.asarray(m) * 255).astype("uint8")).copy()


def dilate(m, r):
    return np.array(_mask_img(m).filter(ImageFilter.MaxFilter(2 * r + 1))) > 127 if r > 0 else m


def erode(m, r):
    return np.array(_mask_img(m).filter(ImageFilter.MinFilter(2 * r + 1))) > 127 if r > 0 else m


def opening(m, r):
    return dilate(erode(m, r), r)


def closing(m, r):
    return erode(dilate(m, r), r)


def outside_of(free):
    """Pixels of free reached from the picture's edge through free (4-connected)."""
    h, w = free.shape
    img = _mask_img(np.pad(free, 1, constant_values=True))
    ImageDraw.floodfill(img, (0, 0), 128)
    return np.array(img)[1:-1, 1:-1] == 128


def parts(mask):
    """Each 4-connected part of mask, as (its pixels, its box) with the box as (y0, y1, x0, x1)."""
    img = _mask_img(mask)
    arr = np.array(img)
    out = []
    while True:
        flat = np.flatnonzero(arr == 255)
        if not len(flat):
            return out
        y, x = divmod(int(flat[0]), arr.shape[1])
        ImageDraw.floodfill(img, (x, y), 128)
        arr = np.array(img)
        comp = arr == 128
        ys, xs = np.nonzero(comp)
        out.append((comp, (ys.min(), ys.max() + 1, xs.min(), xs.max() + 1)))
        arr[comp] = 0
        img = Image.fromarray(arr).copy()  # (a copy: an image made straight from an array can't be drawn on)


def _crop_op(comp, box, margin, fn):
    """fn applied to one part, worked out in a box round it only (the same answer, far quicker)."""
    h, w = comp.shape
    y0, y1, x0, x1 = box
    y0, x0 = max(0, y0 - margin), max(0, x0 - margin)
    y1, x1 = min(h, y1 + margin), min(w, x1 + margin)
    return fn(np.pad(comp[y0:y1, x0:x1], margin))


def rel_lum(rgb):
    c = rgb / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


LP = float(rel_lum(PAGE[None, None])[0, 0])


@lru_cache(maxsize=256)
def analyse(path: str, mtime: int, work: int = 280):
    """What each part of the logo is (at work size): the white it closes in, its thin dark parts, its big dark
    areas, and how far each pixel stands out from the dark page."""
    src = shape(path)
    k = work / max(src.size)
    im = src.resize((max(1, round(src.width * k)), max(1, round(src.height * k))), Image.LANCZOS)
    P = 10
    arr = np.zeros((im.height + 2 * P, im.width + 2 * P, 4), float)
    arr[P:P + im.height, P:P + im.width] = np.array(im, float)
    a = arr[..., 3] / 255
    rgb = arr[..., :3]
    W = max(im.size)
    ow = rgb * a[..., None] + 255 * (1 - a[..., None])                       # as on the game's white page
    whiteish = (ow.min(-1) > 222) & ((ow.max(-1) - ow.min(-1)) < 34)
    ink = ~whiteish
    holes = whiteish & ~outside_of(whiteish)                                  # white the logo closes in
    silhouette = ~outside_of(~ink)
    sil_area = max(1, int(silhouette.sum()))
    inside_white = np.zeros_like(holes)
    r_open = max(2, round(0.018 * W))
    for comp, box in parts(holes):                                            # a broad area, not a letter's middle
        n = int(comp.sum())
        if n >= 0.012 * sil_area and _crop_op(comp, box, 2 * r_open + 2, lambda m: opening(m, r_open)).sum() >= 0.3 * n:
            inside_white |= comp
    deep = erode(silhouette, max(2, round(0.015 * W)))
    semi = opening(deep & (a > 0.3) & (a < 0.97), 2)                         # broad half see-through parts
    white = inside_white | semi
    L = rel_lum(rgb)
    contrast = (np.maximum(L, LP) + 0.05) / (np.minimum(L, LP) + 0.05)
    dark = (a > 0.3) & (contrast < 2.6)                                       # hard to tell from the dark page
    transparent = a < 0.25
    big = np.zeros_like(dark)
    thin = np.zeros_like(dark)
    R = max(3, round(0.045 * W))
    for comp, box in parts(dark):                                             # each dark part judged as a whole
        n = int(comp.sum())
        if n < 4:
            continue
        y0, y1, x0, x1 = box
        sl = (slice(max(0, y0 - 3), y1 + 3), slice(max(0, x0 - 3), x1 + 3))
        c = comp[sl]
        ring = dilate(c, 2) & ~c
        if not ring.any() or (ring & transparent[sl]).sum() < 0.15 * ring.sum():
            continue                                                          # shading inside the logo
        if _crop_op(comp, box, 2 * R + 2, lambda m: opening(m, R)).sum() >= 0.35 * n:
            big |= comp                                                       # keeps its colour, gets an edge line
        else:
            thin |= comp                                                      # writing / outlines: a light tint
    crop = (slice(P, P + im.height), slice(P, P + im.width))
    return white[crop], thin[crop], big[crop], contrast[crop]


def _rs(m, size):
    return np.array(Image.fromarray((m.astype(float) * 255).astype("uint8")).resize(size, Image.LANCZOS)).astype(float) / 255


def dist_to(mask, far):
    h, w = mask.shape
    padded = np.pad(mask, far)
    dist = np.full((h, w), np.inf)
    for dy in range(-far, far + 1):
        for dx in range(-far, far + 1):
            d = math.hypot(dx, dy)
            if d <= far:
                near = padded[far + dy:far + dy + h, far + dx:far + dx + w]
                dist[near] = np.minimum(dist[near], d)
    return dist


def ring(alpha, r: float):
    """A soft line r pixels wide round every visible edge (as a 0-1 mask)."""
    vis = np.array(alpha) > 40
    h, w = vis.shape
    far = int(math.ceil(r)) + 1
    padded = np.pad(vis, far)
    dist = np.full((h, w), np.inf)
    for dy in range(-far, far + 1):
        for dx in range(-far, far + 1):
            d = math.hypot(dx, dy)
            if d <= r + 1:
                near = padded[far + dy:far + dy + h, far + dx:far + dx + w]
                dist[near] = np.minimum(dist[near], d)
    return np.clip(r + 0.5 - dist, 0, 1)


def _over(base_rgb, base_a, top_rgb, top_a):
    oa = top_a + base_a * (1 - top_a)
    rgb = np.where(oa[..., None] > 0, (top_rgb * top_a[..., None] + base_rgb * (base_a * (1 - top_a))[..., None])
                   / np.maximum(oa, 1e-6)[..., None], 0)
    return rgb, oa


def _uri(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def draw(path: str, mtime: int, size: int, style: str = "plain") -> tuple[str, int]:
    """(PNG data URI, pixels to show it at): the logo size pixels across its longest side, in the look style, drawn at
    twice the size so it stays sharp, in a square frame that is the same for every look."""
    src = shape(path)
    s2 = size * 2
    k = s2 / max(src.size)
    im = src.resize((max(1, round(src.width * k)), max(1, round(src.height * k))), Image.LANCZOS)
    r = max(1.2, s2 * 0.008)
    full = s2 + 2 * (int(math.ceil(r)) + 5)
    at = ((full - im.width) // 2, (full - im.height) // 2)
    A = Image.new("L", (full, full), 0)
    A.paste(im.getchannel("A"), at)
    logo = Image.new("RGBA", (full, full), (0, 0, 0, 0))
    logo.paste(im, at)
    canvas = Image.new("RGBA", (full, full), (0, 0, 0, 0))
    if style == "line":
        canvas = Image.new("RGBA", (full, full), tuple(int(v) for v in LINE) + (0,))
        canvas.putalpha(Image.fromarray((ring(A, r) * 0.7 * 255).astype("uint8")))
    elif style == "inside":                                                   # inside the outline on white
        inside = _mask_img(~outside_of(np.array(A) < 160)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.6))
        canvas = Image.new("RGBA", (full, full), (255, 255, 255, 0))
        canvas.putalpha(inside)
    elif style == "whole":                                                    # white behind the whole logo
        m = closing(np.array(A) >= 30, 3)
        inside = _mask_img(~outside_of(~m)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.6))
        canvas = Image.new("RGBA", (full, full), (255, 255, 255, 0))
        canvas.putalpha(inside)
    elif style in ("C", "D"):
        return _uri(_dark_parts(path, mtime, im, at, full, r, style)), full // 2
    canvas.alpha_composite(logo)
    return _uri(canvas), full // 2


def _dark_parts(path, mtime, im, at, full, r, style):
    arr = np.zeros((full, full, 4), float)
    arr[at[1]:at[1] + im.height, at[0]:at[0] + im.width] = np.array(im, float)
    rgb, a = arr[..., :3], arr[..., 3] / 255
    white_m, thin, big, contrast = analyse(path, mtime)

    def place(m):
        z = np.zeros((full, full))
        z[at[1]:at[1] + im.height, at[0]:at[0] + im.width] = _rs(m, im.size)
        return z
    white = place(white_m) if style == "D" else np.zeros((full, full))
    th = place(thin)
    if style == "D":
        th = th * (1 - np.clip(place(white_m.astype(float)), 0, 1))           # dark parts with white under them stay dark
    con = np.zeros((full, full))
    con[at[1]:at[1] + im.height, at[0]:at[0] + im.width] = np.array(
        Image.fromarray(np.clip(contrast * 40, 0, 255).astype("uint8")).resize(im.size, Image.BILINEAR)).astype(float) / 40
    t = (th * np.clip((2.8 - con) / 1.2, 0, 1))[..., None]
    rgb = rgb * (1 - t) + (rgb + (255 - rgb) * 0.74) * t                      # a light tint of its own colour
    out_rgb, out_a = _over(np.ones_like(rgb) * 255, white, rgb, a)
    edge = place(big) > 0.5
    if edge.any():
        edge &= dilate(out_a < 0.2, 1)
        dd = dist_to(edge, int(math.ceil(r)) + 2)
        line = np.clip(r + 0.5 - dd, 0, 1) * (out_a < 0.2) * 0.8
        out_rgb, out_a = _over(np.broadcast_to(LINE, out_rgb.shape), line, out_rgb, out_a)
    return Image.fromarray(np.concatenate([np.clip(out_rgb, 0, 255), np.clip(out_a * 255, 0, 255)[..., None]],
                                          axis=2).astype("uint8"), "RGBA")
