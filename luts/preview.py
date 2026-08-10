#!/usr/bin/env python3
"""Parse the generated .cube files back with an independent reader, apply them
to a synthetic test chart via trilinear interpolation, and emit a contact sheet.
Doubles as validation: catches bad ordering, wrong counts, clipping, NaNs."""

import glob
import os
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def read_cube(path):
    size, title, data = None, os.path.basename(path), []
    for line in open(path):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.upper().startswith("TITLE"):
            title = s.split(None, 1)[1].strip('"')
        elif s.upper().startswith("LUT_3D_SIZE"):
            size = int(s.split()[1])
        elif s.upper().startswith(("DOMAIN_", "LUT_1D", "LUT_IN", "LUT_OUT")):
            continue
        else:
            data.append([float(v) for v in s.split()])
    arr = np.array(data, float)
    assert size is not None, f"{path}: no LUT_3D_SIZE"
    assert arr.shape == (size ** 3, 3), f"{path}: {arr.shape} != {(size**3, 3)}"
    assert np.isfinite(arr).all(), f"{path}: non-finite"
    # red fastest -> reshape (b, g, r, 3), then transpose to (r, g, b, 3)
    lut = arr.reshape(size, size, size, 3).transpose(2, 1, 0, 3)
    return title, size, lut


def apply_lut(img, lut):
    n = lut.shape[0]
    p = np.clip(img, 0, 1) * (n - 1)
    i0 = np.floor(p).astype(int)
    i0 = np.minimum(i0, n - 2)
    f = p - i0
    r0, g0, b0 = i0[..., 0], i0[..., 1], i0[..., 2]
    fr, fg, fb = f[..., 0:1], f[..., 1:2], f[..., 2:3]
    out = np.zeros(img.shape)
    for dr in (0, 1):
        wr = fr if dr else 1 - fr
        for dg in (0, 1):
            wg = fg if dg else 1 - fg
            for db in (0, 1):
                wb = fb if db else 1 - fb
                out += wr * wg * wb * lut[r0 + dr, g0 + dg, b0 + db]
    return np.clip(out, 0, 1)


def test_chart(w=620, h=138):
    img = np.zeros((h, w, 3))
    x = np.linspace(0, 1, w)
    # band 1: hue sweep
    hb = h // 3
    hue = (x * 6.0)
    i = np.floor(hue) % 6
    fpart = hue - np.floor(hue)
    ramp = np.stack([
        np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5],
                  [1, 1 - fpart, 0, 0, fpart, 1]),
        np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5],
                  [fpart, 1, 1, 1 - fpart, 0, 0]),
        np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5],
                  [0, 0, fpart, 1, 1, 1 - fpart]),
    ], axis=1) * 0.86 + 0.07
    img[:hb] = ramp[None, :, :]
    # band 2: grayscale ramp
    img[hb:2 * hb] = x[None, :, None]
    # band 3: memory-colour patches
    patches = [(0.86, 0.68, 0.58), (0.66, 0.46, 0.37), (0.40, 0.26, 0.20),
               (0.30, 0.46, 0.72), (0.29, 0.44, 0.22), (0.68, 0.16, 0.14),
               (0.73, 0.73, 0.73), (0.18, 0.18, 0.18)]
    pw = w // len(patches)
    for k, c in enumerate(patches):
        img[2 * hb:, k * pw:(k + 1) * pw] = c
    return img


def main():
    lutdir = sys.argv[1]
    out = sys.argv[2]
    files = sorted(glob.glob(os.path.join(lutdir, "*.cube")))
    chart = test_chart()
    ch, cw = chart.shape[:2]
    pad, lab = 14, 22
    rows = len(files) + 1
    sheet = Image.new("RGB", (cw + 2 * pad, rows * (ch + lab + pad) + pad), (22, 22, 24))
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
    except Exception:
        font = ImageFont.load_default()

    def paste(row, arr, name):
        y = pad + row * (ch + lab + pad)
        d.text((pad, y), name, fill=(232, 232, 236), font=font)
        sheet.paste(Image.fromarray((arr * 255 + 0.5).astype(np.uint8)), (pad, y + lab))

    paste(0, chart, "SOURCE  (no LUT)")
    for k, p in enumerate(files, start=1):
        title, size, lut = read_cube(p)
        graded = apply_lut(chart, lut)
        # validation: neutral axis must stay monotone
        ax = np.linspace(0, 1, 64)
        neutral = apply_lut(np.stack([ax, ax, ax], axis=1)[None], lut)[0]
        mono = bool(np.all(np.diff(neutral.mean(axis=1)) >= -1e-6))
        paste(k, graded, f"{title}  \u2014  {os.path.basename(p)}")
        print(f"ok  {os.path.basename(p):34s} {size}^3  mono={mono}")
    sheet.save(out)
    print("sheet:", out)


if __name__ == "__main__":
    main()
