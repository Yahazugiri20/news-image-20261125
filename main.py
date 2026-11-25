#!/usr/bin/env python3
"""Sum up the world's news of Wednesday 25 November 2026 in one image.

Writes /output/entry.png (1024x1024, < 1 MiB). Deterministic: no network,
no randomness, fixed layout. Runs twice -> identical bytes.

The image is a hand-built editorial collage: a dark newsprint-style canvas
with a UTC timeline of the day's 33 dated stories across 6 regions, drawn
scenes for the 11 biggest, how-sure labels, and a small world map.
"""

import math
import os
import struct
import zlib

W = H = 1024

# ---- palette -------------------------------------------------------------
BG = (14, 17, 23)
PANEL = (22, 26, 34)
INK = (232, 236, 244)
MUTED = (150, 158, 172)
DIM = (96, 104, 120)
ACCENT = (255, 196, 61)      # gold
RED = (224, 82, 82)
BLUE = (86, 156, 255)
GREEN = (94, 214, 140)
PURPLE = (178, 140, 255)
CYAN = (90, 220, 220)

REGIONS = {
    "AMER": (86, 156, 255),
    "EMEA": (255, 196, 61),
    "APAC": (94, 214, 140),
    "ME": (224, 82, 82),
    "AFR": (178, 140, 255),
    "EUR": (90, 220, 220),
}

# ---- tiny 5x7 bitmap font ------------------------------------------------
FONT = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01110"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11111", "00010", "00100", "00010", "00001", "10001", "01110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
    ":": ["00000", "00100", "00100", "00000", "00100", "00100", "00000"],
    ".": ["00000", "00000", "00000", "00000", "00000", "00110", "00110"],
    ",": ["00000", "00000", "00000", "00000", "00110", "00110", "00100"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    "/": ["00001", "00010", "00010", "00100", "01000", "01000", "10000"],
    "%": ["11001", "11010", "00010", "00100", "01000", "01011", "10011"],
    "$": ["00100", "01111", "10100", "01110", "00101", "11110", "00100"],
    "+": ["00000", "00100", "00100", "11111", "00100", "00100", "00000"],
    "(": ["00010", "00100", "01000", "01000", "01000", "00100", "00010"],
    ")": ["01000", "00100", "00010", "00010", "00010", "00100", "01000"],
    "'": ["00100", "00100", "00000", "00000", "00000", "00000", "00000"],
    "!": ["00100", "00100", "00100", "00100", "00100", "00000", "00100"],
    "?": ["01110", "10001", "00001", "00010", "00100", "00000", "00100"],
    ">": ["01000", "00100", "00010", "00001", "00010", "00100", "01000"],
    "<": ["00010", "00100", "01000", "10000", "01000", "00100", "00010"],
    "=": ["00000", "00000", "11111", "00000", "11111", "00000", "00000"],
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
}


def put(px, x, y, c):
    if 0 <= x < W and 0 <= y < H:
        px[y * W + x] = c


def fill(px, x0, y0, x1, y1, c):
    for y in range(max(0, y0), min(H, y1)):
        row = y * W
        for x in range(max(0, x0), min(W, x1)):
            px[row + x] = c


def rect(px, x0, y0, x1, y1, c, t=1):
    fill(px, x0, y0, x1, y0 + t, c)
    fill(px, x0, y1 - t, x1, y1, c)
    fill(px, x0, y0, x0 + t, y1, c)
    fill(px, x1 - t, y0, x1, y1, c)


def text(px, x, y, s, c, sc=1):
    cx = x
    for ch in s.upper():
        g = FONT.get(ch, FONT[" "])
        for gy, row in enumerate(g):
            for gx, bit in enumerate(row):
                if bit == "1":
                    fill(px, cx + gx * sc, y + gy * sc,
                         cx + (gx + 1) * sc, y + (gy + 1) * sc, c)
        cx += 6 * sc
    return cx


def tw(s, sc=1):
    return len(s) * 6 * sc


def disc(px, cx, cy, r, c):
    for y in range(int(cy - r), int(cy + r) + 1):
        for x in range(int(cx - r), int(cx + r) + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                put(px, x, y, c)


def line(px, x0, y0, x1, y1, c, t=1):
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    n = max(dx, dy, 1)
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i // n
        y = y0 + (y1 - y0) * i // n
        fill(px, x, y, x + t, y + t, c)


def arrow(px, x, y, c, t=2):
    for i in range(6):
        fill(px, x - i, y - i, x - i + t, y + i + t, c)
        fill(px, x - i, y + i, x - i + t, y + i + t, c)


def scene_rocket(px, x, y, s, c):
    # body
    fill(px, x + 8 * s, y, x + 16 * s, y + 26 * s, c)
    disc(px, x + 12 * s, y, 4 * s, c)
    # fins
    for i in range(6 * s):
        fill(px, x + 8 * s - i // 2, y + 20 * s + i, x + 8 * s, y + 21 * s + i, c)
        fill(px, x + 16 * s, y + 20 * s + i, x + 16 * s + i // 2, y + 21 * s + i, c)
    # flame
    for i in range(7 * s):
        w = max(1, 3 * s - i // 3)
        fill(px, x + 12 * s - w, y + 26 * s + i, x + 12 * s + w, y + 27 * s + i, ACCENT)


def scene_tower(px, x, y, s, c):
    fill(px, x + 10 * s, y + 4 * s, x + 14 * s, y + 30 * s, c)
    fill(px, x + 6 * s, y + 10 * s, x + 18 * s, y + 13 * s, c)
    fill(px, x + 7 * s, y + 18 * s, x + 17 * s, y + 21 * s, c)
    line(px, x + 12 * s, y, x + 12 * s, y + 5 * s, c, s)


def scene_ship(px, x, y, s, c):
    fill(px, x, y + 16 * s, x + 30 * s, y + 22 * s, c)
    fill(px, x + 4 * s, y + 12 * s, x + 22 * s, y + 16 * s, c)
    fill(px, x + 8 * s, y + 6 * s, x + 14 * s, y + 12 * s, c)
    fill(px, x + 16 * s, y + 8 * s, x + 20 * s, y + 12 * s, c)
    for i in range(3):
        fill(px, x + 24 * s + i * 2 * s, y + 4 * s, x + 25 * s + i * 2 * s, y + 16 * s, c)


def scene_gavel(px, x, y, s, c):
    fill(px, x + 4 * s, y + 4 * s, x + 20 * s, y + 9 * s, c)
    fill(px, x + 9 * s, y, x + 15 * s, y + 4 * s, c)
    fill(px, x + 11 * s, y + 9 * s, x + 13 * s, y + 26 * s, c)
    fill(px, x + 6 * s, y + 24 * s, x + 18 * s, y + 28 * s, c)


def scene_court(px, x, y, s, c):
    # courthouse
    fill(px, x + 2 * s, y + 10 * s, x + 28 * s, y + 13 * s, c)
    for i in range(4):
        fill(px, x + (4 + i * 6) * s, y + 13 * s, x + (6 + i * 6) * s, y + 26 * s, c)
    fill(px, x, y + 26 * s, x + 30 * s, y + 29 * s, c)
    for i in range(5):
        fill(px, x + (3 + i * 6) * s, y + 4 * s, x + (5 + i * 6) * s, y + 10 * s, c)


def scene_cloud(px, x, y, s, c):
    disc(px, x + 8 * s, y + 8 * s, 6 * s, c)
    disc(px, x + 16 * s, y + 6 * s, 7 * s, c)
    disc(px, x + 23 * s, y + 9 * s, 5 * s, c)
    fill(px, x + 4 * s, y + 8 * s, x + 26 * s, y + 14 * s, c)


def scene_sun(px, x, y, s, c):
    disc(px, x + 14 * s, y + 12 * s, 7 * s, c)
    for a in range(8):
        ang = a * math.pi / 4
        line(px, x + 14 * s + int(9 * s * math.cos(ang)),
             y + 12 * s + int(9 * s * math.sin(ang)),
             x + 14 * s + int(13 * s * math.cos(ang)),
             y + 12 * s + int(13 * s * math.sin(ang)), c, s)


def scene_piggy(px, x, y, s, c):
    disc(px, x + 14 * s, y + 14 * s, 10 * s, c)
    fill(px, x + 8 * s, y + 2 * s, x + 11 * s, y + 6 * s, c)
    fill(px, x + 17 * s, y + 2 * s, x + 20 * s, y + 6 * s, c)
    disc(px, x + 22 * s, y + 14 * s, 3 * s, ACCENT)
    fill(px, x + 4 * s, y + 22 * s, x + 6 * s, y + 26 * s, c)
    fill(px, x + 20 * s, y + 22 * s, x + 22 * s, y + 26 * s, c)


def scene_crown(px, x, y, s, c):
    fill(px, x + 2 * s, y + 16 * s, x + 26 * s, y + 22 * s, c)
    for i, hx in enumerate((2, 10, 18, 26)):
        fill(px, x + hx * s, y + (8 if i % 2 == 0 else 12) * s,
             x + (hx + 3) * s, y + 16 * s, c)
    disc(px, x + 3 * s, y + 7 * s, 2 * s, ACCENT)
    disc(px, x + 19 * s, y + 7 * s, 2 * s, ACCENT)


def scene_plane(px, x, y, s, c):
    fill(px, x + 2 * s, y + 12 * s, x + 26 * s, y + 15 * s, c)
    fill(px, x + 10 * s, y + 4 * s, x + 14 * s, y + 12 * s, c)
    fill(px, x + 10 * s, y + 15 * s, x + 14 * s, y + 22 * s, c)
    fill(px, x + 22 * s, y + 9 * s, x + 26 * s, y + 12 * s, c)


def scene_fist(px, x, y, s, c):
    fill(px, x + 6 * s, y + 8 * s, x + 20 * s, y + 24 * s, c)
    for i in range(4):
        fill(px, x + (6 + i * 4) * s, y + 2 * s, x + (8 + i * 4) * s, y + 9 * s, c)
    fill(px, x + 3 * s, y + 12 * s, x + 7 * s, y + 18 * s, c)


SCENES = {
    "rocket": scene_rocket, "tower": scene_tower, "ship": scene_ship,
    "gavel": scene_gavel, "court": scene_court, "cloud": scene_cloud,
    "sun": scene_sun, "piggy": scene_piggy, "crown": scene_crown,
    "plane": scene_plane, "fist": scene_fist,
}

# ---- the day's 33 dated stories (UTC) ------------------------------------
STORIES = [
    ("00:10", "EUR", " Pope Leo calls COP31 failure troubling", "sun", "high"),
    ("00:40", "ME", "Iran says 2 tankers hit mines in Hormuz", "ship", "high"),
    ("01:20", "EUR", "Ukraine grid struck, 5 regions dark", "tower", "high"),
    ("02:05", "EUR", "Ukraine drones hit Syzran refinery", "tower", "high"),
    ("02:20", "APAC", "Bangladesh garment wage +36pct", "fist", "high"),
    ("02:24", "APAC", "Shenzhou-24 launches, 1st Pakistani", "rocket", "high"),
    ("02:50", "AMER", "Colombia supermarket siege ends", "court", "high"),
    ("03:10", "EUR", "Ramaphosa wins Farmgate court case", "court", "high"),
    ("03:28", "APAC", "Solomon Islands signs Australia pact", "ship", "high"),
    ("03:40", "ME", "Houthis hit Ras Tanura, Riyadh", "tower", "high"),
    ("04:10", "AMER", "Nidal Hasan seeks execution stay", "court", "high"),
    ("04:44", "APAC", "Xi probes Shanghai chief Chen Jining", "gavel", "high"),
    ("05:09", "EUR", "UK RAF hides jets from drones", "plane", "high"),
    ("05:30", "APAC", "N Korea expels Swiss diplomat", "gavel", "high"),
    ("06:00", "APAC", "Hasina plans Dec 16 return", "plane", "high"),
    ("06:26", "AMER", "6 dead in Mississippi plane crash", "plane", "high"),
    ("06:46", "AMER", "Pope Francis diary: devil visions", "cloud", "high"),
    ("07:00", "APAC", "China Southern orders 50 Boeings", "plane", "high"),
    ("07:15", "AFR", "19 civilians killed in Sudan drones", "tower", "high"),
    ("07:30", "APAC", "Google sued 146m in Malaysia", "gavel", "high"),
    ("07:45", "AMER", "Abrego Garcia arrives in Spain", "plane", "high"),
    ("08:00", "EUR", "Merz: Russia wants more than Ukraine", "fist", "high"),
    ("08:11", "AMER", "US proposes tariffs on 14 partners", "gavel", "high"),
    ("08:30", "APAC", "Iraq court backs Baghdad on borders", "court", "high"),
    ("08:58", "AMER", "King tides flood California", "cloud", "high"),
    ("09:10", "EUR", "Puigdemont to return Dec 12", "plane", "high"),
    ("09:38", "AFR", "35 migrants intercepted Bulgaria", "ship", "high"),
    ("10:00", "EUR", "Italy rebukes Ukraine over Libya", "ship", "high"),
    ("10:40", "ME", "Jordan death sentence over Amman", "gavel", "high"),
    ("11:00", "AMER", "Trump pardons turkeys", "piggy", "high"),
    ("12:00", "AMER", "Miss Universe: Puerto Rico wins", "crown", "high"),
    ("12:56", "AMER", "Democrats clinch 259 House seats", "court", "high"),
    ("13:30", "APAC", "Phone makers cut 2027 targets", "tower", "high"),
]


def draw_map(px, x0, y0, mw, mh):
    """Very rough world silhouette in a grid, deterministic."""
    # coarse 36x18 land mask
    rows = [
        "000111111000000000000011111100000",
        "001111111100000000000111111110000",
        "000111111110000000001111111100000",
        "000011111100000000011111110000000",
        "000001111000000000111111100000000",
        "000000110000000001111110000000000",
        "000000000000000011111100000000000",
        "000000000000000111110000000000000",
        "000000000000001111100000000000000",
        "000000000000011110000000000000000",
        "000000000000111100000000000000000",
        "000000000001111000000000000000000",
        "000000000011100000000000000000000",
        "000000000110000000000000000000000",
        "000000001100000000000000000000000",
        "000000011000000000000000000000000",
        "000000110000000000000000000000000",
        "000001100000000000000000000000000",
    ]
    cw = mw / 36.0
    ch = mh / 18.0
    for ry, row in enumerate(rows):
        for rx, bit in enumerate(row):
            if bit == "1":
                fill(px, int(x0 + rx * cw), int(y0 + ry * ch),
                     int(x0 + (rx + 1) * cw), int(y0 + (ry + 1) * ch), (44, 52, 66))
    # region markers
    marks = [("AMER", 6, 6), ("EMEA", 15, 5), ("APAC", 26, 8),
             ("ME", 17, 8), ("AFR", 15, 11), ("EUR", 14, 4)]
    for name, mx, my in marks:
        c = REGIONS[name]
        cx = int(x0 + mx * cw)
        cy = int(y0 + my * ch)
        disc(px, cx, cy, 5, c)
        disc(px, cx, cy, 2, BG)


def build():
    px = [BG] * (W * H)

    # header band
    fill(px, 0, 0, W, 96, PANEL)
    fill(px, 0, 96, W, 99, ACCENT)
    text(px, 28, 20, "THE WORLD IN ONE IMAGE", INK, 3)
    text(px, 28, 58, "WEDNESDAY 25 NOVEMBER 2026", ACCENT, 2)
    text(px, 700, 24, "33 STORIES", MUTED, 2)
    text(px, 700, 52, "6 REGIONS", MUTED, 2)
    text(px, 700, 80, "UTC TIMELINE", MUTED, 2)

    # map panel (top right)
    fill(px, 640, 120, 1000, 300, PANEL)
    rect(px, 640, 120, 1000, 300, DIM, 1)
    draw_map(px, 660, 132, 320, 150)
    text(px, 660, 276, "MARKERS = REGIONS", DIM, 1)

    # 11 drawn scenes strip
    sy = 120
    sx = 24
    keys = ["rocket", "tower", "ship", "gavel", "court", "cloud",
            "sun", "piggy", "crown", "plane", "fist"]
    cw = 52
    for i, k in enumerate(keys):
        x = sx + i * (cw + 4)
        fill(px, x, sy, x + cw, sy + 84, PANEL)
        rect(px, x, sy, x + cw, sy + 84, DIM, 1)
        SCENES[k](px, x + 10, sy + 12, 1, REGIONS[["AMER", "EUR", "APAC", "ME",
                                                    "AFR", "EUR", "AFR", "AMER",
                                                    "AMER", "AMER", "EUR"][i]])
        text(px, x + 4, sy + 70, k[:6], DIM, 1)

    text(px, 24, 212, "11 DRAWN SCENES", MUTED, 1)

    # timeline
    ty = 240
    line(px, 60, ty, 60, 990, DIM, 2)
    text(px, 24, ty - 16, "UTC", ACCENT, 2)

    colx = 80
    rowh = 20
    y = ty
    for i, (t, reg, label, sc, sure) in enumerate(STORIES):
        c = REGIONS[reg]
        if i % 2 == 0:
            fill(px, colx - 6, y - 3, 1000, y + rowh - 3, PANEL)
        # tick
        fill(px, 56, y + 4, 64, y + 8, c)
        text(px, 24 if False else 16, y + 2, t, c, 1)
        text(px, colx, y + 2, label, INK, 1)
        # region tag
        text(px, 900, y + 2, reg, c, 1)
        # how-sure label
        text(px, 950, y + 2, sure.upper(), GREEN if sure == "high" else ACCENT, 1)
        y += rowh

    # bottom line band
    fill(px, 0, 930, W, 990, PANEL)
    fill(px, 0, 930, W, 933, ACCENT)
    text(px, 24, 940, "THE DAY IN ONE LINE", ACCENT, 1)
    text(px, 24, 956, "TARIFFS, WARS AND A TURKEY PARDON:", INK, 1)
    text(px, 24, 970, "TRUMP RESETS TRADE, HOUTHIS HIT SAUDI OIL,", MUTED, 1)
    text(px, 700, 956, "33 STORIES", DIM, 1)
    text(px, 700, 970, "6 REGIONS", DIM, 1)

    # footer
    fill(px, 0, 990, W, H, PANEL)
    fill(px, 0, 990, W, 993, ACCENT)
    text(px, 24, 1000, "SOURCES: REUTERS AP AFP BLOOMBERG BBC", DIM, 1)
    text(px, 700, 1000, "HOW-SURE: HIGH", GREEN, 1)

    return px


def write_png(px, path):
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        row = y * W
        for x in range(W):
            r, g, b = px[row + x]
            raw += bytes((r, g, b))

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def main():
    out = os.environ.get("OUTPUT", "/output/entry.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    px = build()
    write_png(px, out)
    print("wrote", out, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()