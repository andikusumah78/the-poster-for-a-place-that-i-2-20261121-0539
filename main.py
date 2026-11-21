#!/usr/bin/env python3
"""AURELIA — a travel poster for a place that isn't there.

Pure-stdlib Python 3.13. Writes one 1024x1024 PNG to $MAKEFUN_OUTPUT_DIR/entry.png
(or /output/entry.png). No network, fully deterministic (fixed seed, no time).
"""
import math
import os
import random
import struct
import zlib

W = H = 1024
fb = bytearray(W * H * 3)

# ---------------------------------------------------------------- raster helpers
def fill_rect(x, y, w, h, color):
    r, g, b = color
    row = bytes((r, g, b)) * w
    x0 = max(0, x)
    x1 = min(W, x + w)
    if x1 <= x0:
        return
    w2 = x1 - x0
    row = bytes((r, g, b)) * w2
    off = (x0 - x) * 3
    row = row[off:] if False else bytes((r, g, b)) * w2
    for yy in range(max(0, y), min(H, y + h)):
        i = (yy * W + x0) * 3
        fb[i:i + w2 * 3] = row


def blend_px(x, y, r, g, b, a):
    if 0 <= x < W and 0 <= y < H and a > 0.0:
        if a > 1.0:
            a = 1.0
        i = (y * W + x) * 3
        fb[i] = int(fb[i] * (1.0 - a) + r * a)
        fb[i + 1] = int(fb[i + 1] * (1.0 - a) + g * a)
        fb[i + 2] = int(fb[i + 2] * (1.0 - a) + b * a)


def fill_span(y, x0, x1, color):
    if y < 0 or y >= H:
        return
    x0 = max(0, x0)
    x1 = min(W - 1, x1)
    if x1 < x0:
        return
    r, g, b = color
    i = (y * W + x0) * 3
    fb[i:(i + (x1 - x0 + 1) * 3)] = bytes((r, g, b)) * (x1 - x0 + 1)


def fill_circle(cx, cy, rad, color):
    for y in range(cy - rad, cy + rad + 1):
        dy = y - cy
        dx = int(math.sqrt(max(0, rad * rad - dy * dy)))
        fill_span(y, cx - dx, cx + dx, color)


def fill_ellipse(cx, cy, rx, ry, color):
    for y in range(cy - ry, cy + ry + 1):
        dy = (y - cy) / ry
        dx = int(rx * math.sqrt(max(0.0, 1.0 - dy * dy)))
        fill_span(y, cx - dx, cx + dx, color)


def fill_poly(points, color):
    # scanline fill, points = list of (x, y)
    ys = [p[1] for p in points]
    for y in range(max(0, min(ys)), min(H - 1, max(ys)) + 1):
        xs = []
        n = len(points)
        for k in range(n):
            x1, y1 = points[k]
            x2, y2 = points[(k + 1) % n]
            if (y1 <= y < y2) or (y2 <= y < y1):
                t = (y - y1) / (y2 - y1)
                xs.append(int(x1 + t * (x2 - x1)))
        xs.sort()
        for j in range(0, len(xs) - 1, 2):
            fill_span(y, xs[j], xs[j + 1], color)


def soft_disc(cx, cy, rad, color, strength):
    """Radial falloff glow disc, alpha (1-d/r)^2 * strength."""
    x0 = max(0, cx - rad)
    x1 = min(W - 1, cx + rad)
    y0 = max(0, cy - rad)
    y1 = min(H - 1, cy + rad)
    r, g, b = color
    for y in range(y0, y1 + 1):
        dy = (y - cy) / rad
        for x in range(x0, x1 + 1):
            dx = (x - cx) / rad
            d = dx * dx + dy * dy
            if d < 1.0:
                a = (1.0 - d) * (1.0 - d) * strength
                blend_px(x, y, r, g, b, a)


def soft_ellipse(cx, cy, rx, ry, color, strength):
    x0 = max(0, cx - rx)
    x1 = min(W - 1, cx + rx)
    y0 = max(0, cy - ry)
    y1 = min(H - 1, cy + ry)
    r, g, b = color
    for y in range(y0, y1 + 1):
        dy = (y - cy) / ry
        for x in range(x0, x1 + 1):
            dx = (x - cx) / rx
            d = dx * dx + dy * dy
            if d < 1.0:
                a = (1.0 - d) * (1.0 - d) * strength
                blend_px(x, y, r, g, b, a)


def lerp(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


# ---------------------------------------------------------------- sky gradient
STOPS = [
    (0, (24, 18, 60)),
    (260, (66, 34, 92)),
    (470, (150, 66, 104)),
    (600, (228, 140, 88)),
    (700, (250, 196, 128)),
    (820, (238, 176, 140)),
    (1024, (150, 92, 108)),
]
row_colors = []
for y in range(H):
    for k in range(len(STOPS) - 1):
        y1, c1 = STOPS[k]
        y2, c2 = STOPS[k + 1]
        if y1 <= y <= y2:
            t = (y - y1) / max(1, y2 - y1)
            row_colors.append(lerp(c1, c2, t))
            break
    else:
        row_colors.append(STOPS[-1][1])
for y in range(H):
    r, g, b = row_colors[y]
    i = y * W * 3
    fb[i:i + W * 3] = bytes((r, g, b)) * W

rng = random.Random(20261121)

# ---------------------------------------------------------------- stars
for _ in range(190):
    x = rng.randint(0, W - 1)
    y = rng.randint(0, 500)
    v = rng.randint(140, 255)
    s = rng.random()
    if s < 0.75:
        blend_px(x, y, v, v, min(255, v + 20), 0.9)
    else:
        fill_rect(x, y, 2, 2, (v, v, min(255, v + 20)))

# ---------------------------------------------------------------- sun glow on the horizon
soft_disc(400, 640, 300, (255, 196, 120), 0.55)
soft_disc(400, 640, 150, (255, 220, 160), 0.55)

# ---------------------------------------------------------------- ringed planet
PCX, PCY, PR = 710, 265, 118
# ring, back half (full band first; planet covers the middle)
ANG = math.radians(-18)
COSA, SINA = math.cos(ANG), math.sin(ANG)


def ring_band(y_lo, y_hi):
    for y in range(max(0, y_lo), min(H, y_hi + 1)):
        for x in range(PCX - 215, PCX + 216):
            dx = x - PCX
            dy = y - PCY
            rx_ = dx * COSA + dy * SINA
            ry_ = -dx * SINA + dy * COSA
            outer = (rx_ / 205.0) ** 2 + (ry_ / 54.0) ** 2
            inner = (rx_ / 182.0) ** 2 + (ry_ / 43.0) ** 2
            if outer <= 1.0 and inner >= 1.0:
                blend_px(x, y, 232, 196, 128, 0.92)


ring_band(PCY - 70, PCY + 70)
# planet disc with soft horizontal bands
for y in range(PCY - PR, PCY + PR + 1):
    dy = y - PCY
    dx = int(math.sqrt(max(0, PR * PR - dy * dy)))
    band = (y - (PCY - PR)) % 26
    if band < 7:
        col = (226, 190, 128)
    elif band < 13:
        col = (240, 214, 164)
    else:
        col = (236, 204, 148)
    fill_span(y, PCX - dx, PCX + dx, col)
# planet rim light on the lower-left (facing the sun)
for y in range(PCY - PR, PCY + PR + 1):
    dy = y - PCY
    dx = int(math.sqrt(max(0, PR * PR - dy * dy)))
    fill_span(y, PCX - dx, PCX - dx + 5, (250, 226, 176))
# ring, front half (below the planet's centre line)
ring_band(PCY + 1, PCY + 70)

# ---------------------------------------------------------------- airship
fill_ellipse(310, 330, 56, 14, (214, 92, 70))
fill_ellipse(310, 326, 50, 8, (232, 122, 88))
fill_rect(258, 330, 104, 2, (240, 150, 110))
fill_rect(292, 344, 34, 9, (52, 36, 60))
fill_rect(300, 347, 5, 3, (255, 236, 190))
fill_rect(314, 347, 5, 3, (255, 236, 190))
fill_poly([(362, 324), (376, 316), (358, 332)], (196, 80, 62))

# ---------------------------------------------------------------- birds
for bx, by in [(250, 220), (292, 204), (560, 178), (624, 238), (852, 196), (180, 300)]:
    for t in range(7):
        blend_px(bx - t, by + t // 2, 28, 22, 52, 0.9)
        blend_px(bx + t, by + t // 2, 28, 22, 52, 0.9)

# ---------------------------------------------------------------- floating islands
DARK = (40, 30, 68)
LIT = (198, 152, 82)
GREEN = (52, 84, 62)


def island(top_left, top_right, tip, trees=True, fall=True):
    x1, y1 = top_left
    x2, y2 = top_right
    tx, ty = tip
    pts = [
        (x1, y1), (x2, y2),
        (x2 - 14, y2 + 42), (tx + 26, ty - 42), (tx, ty),
        (tx - 26, ty - 42), (x1 + 14, y1 + 42),
    ]
    fill_poly(pts, DARK)
    # lit top surface
    fill_poly([(x1, y1), (x2, y2), (x2 - 6, y2 + 12), (x1 + 6, y1 + 12)], LIT)
    if trees:
        for gx in range(x1 + 26, x2 - 20, 34):
            fill_poly([(gx, y1 - 16), (gx + 9, y1 + 2), (gx - 9, y1 + 2)], GREEN)
    if fall:
        for fx in (tx - 5, tx + 5):
            for yy in range(ty, ty + 96):
                a = 0.62 * (1.0 - (yy - ty) / 96.0)
                for xx in range(fx - 3, fx + 4):
                    blend_px(xx, yy, 205, 224, 238, a)
        soft_ellipse(tx, ty + 100, 34, 12, (232, 214, 196), 0.5)


island((120, 498), (238, 498), (179, 588), trees=False, fall=False)
island((668, 462), (836, 462), (752, 578), trees=True, fall=True)
island((300, 556), (560, 556), (430, 716), trees=True, fall=True)
# lighthouse on the main island
fill_rect(516, 522, 12, 34, (240, 222, 190))
fill_poly([(514, 522), (530, 522), (522, 510)], (214, 92, 70))
soft_disc(522, 508, 14, (255, 240, 180), 0.8)

# ---------------------------------------------------------------- sea of clouds
for _ in range(26):
    cx = rng.randint(-40, W + 40)
    cy = rng.randint(790, 1000)
    rx = rng.randint(90, 210)
    ry = rng.randint(24, 48)
    col = rng.choice([(255, 226, 192), (250, 202, 176), (240, 182, 170), (255, 238, 210)])
    soft_ellipse(cx, cy, rx, ry, col, 0.75)
# a few distant puffs above the horizon
for cx, cy, rx, ry in [(180, 690, 90, 20), (700, 668, 120, 22), (880, 700, 80, 18)]:
    soft_ellipse(cx, cy, rx, ry, (250, 210, 180), 0.6)

# ---------------------------------------------------------------- title: AURELIA (only text on the poster)
GLYPHS = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
}
NAME = "AURELIA"
S = 13  # glyph scale: 5*13 wide, 7*13 tall
GW, GH = 5 * S, 7 * S
GAP = S
total_w = len(NAME) * GW + (len(NAME) - 1) * GAP
x0 = (W - total_w) // 2
y0 = 838
# gold rule above the title
fill_rect(x0 + 8, 812, total_w - 16, 3, (232, 185, 106))


def draw_name(ox, oy, color):
    x = x0 + ox
    for ch in NAME:
        g = GLYPHS[ch]
        for r in range(7):
            for c in range(5):
                if g[r][c] == "1":
                    fill_rect(x + c * S + ox * 0, y0 + r * S + oy, S, S, color)
        x += GW + GAP


draw_name(4, 5, (36, 24, 66))          # soft shadow
draw_name(0, 0, (255, 242, 207))      # cream letters

# ---------------------------------------------------------------- write PNG
out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
os.makedirs(out_dir, exist_ok=True)
path = os.path.join(out_dir, "entry.png")

raw = bytearray()
for y in range(H):
    raw.append(0)  # filter: None
    raw += fb[y * W * 3:(y + 1) * W * 3]


def chunk(typ, data):
    return (
        struct.pack(">I", len(data)) + typ + data +
        struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    )


ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
png = b"\x89PNG\r\n\x1a\n"
png += chunk(b"IHDR", ihdr)
png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
png += chunk(b"IEND", b"")
with open(path, "wb") as f:
    f.write(png)
print("wrote", path, len(png), "bytes")
