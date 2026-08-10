#!/usr/bin/env python3
"""
lutgen.py — parametric generator for Adobe .cube 3D LUTs.

Format notes (Adobe Cube LUT Specification 1.0):
  - Text file. Optional TITLE, LUT_3D_SIZE N (2..256), DOMAIN_MIN/DOMAIN_MAX.
  - N**3 RGB triplets, floats, RED index varies FASTEST, then green, then blue.
  - Values outside [0,1] are legal (DOMAIN_MAX can exceed 1) but most NLEs clamp.

Everything below operates on display-referred (already gamma-encoded) RGB in
[0,1], which is how creative LUTs are normally applied in Resolve/Premiere/
ffmpeg. Ops are vectorised over an (M,3) array of grid samples.

Usage:  python3 lutgen.py [outdir]
"""

import sys
import os
import numpy as np

# ---------------------------------------------------------------- primitives

# Rec.709 luma weights (use for display-space luma)
W709 = np.array([0.2126, 0.7152, 0.0722])


def srgb_to_lin(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


def luma(rgb, w=W709):
    return rgb @ w


def s_curve(x, strength=0.35, pivot=0.435):
    """Contrast S-curve with fixed endpoints, C1-continuous at the pivot.

    strength 0 = identity. Both branches have slope k=1+strength at the pivot,
    so no kink shows up on a gradient.
    """
    if strength == 0:
        return x
    k = 1.0 + strength
    x = np.clip(x, 0.0, 1.0)
    lo = pivot * np.power(np.clip(x / pivot, 0, None), k)
    hi = 1.0 - (1.0 - pivot) * np.power(np.clip((1.0 - x) / (1.0 - pivot), 0, None), k)
    return np.where(x < pivot, lo, hi)


def lift_gamma_gain(rgb, lift=(0, 0, 0), gamma=(1, 1, 1), gain=(1, 1, 1)):
    lift = np.asarray(lift, float)
    gamma = np.asarray(gamma, float)
    gain = np.asarray(gain, float)
    y = lift + (gain - lift) * rgb
    y = np.clip(y, 0.0, 1.0)
    return np.power(y, 1.0 / gamma)


def saturation(rgb, sat, w=W709):
    l = luma(rgb, w)[:, None]
    return l + (rgb - l) * sat


def vibrance(rgb, amount, w=W709):
    """Saturation weighted down on already-saturated pixels (protects skin)."""
    l = luma(rgb, w)[:, None]
    chroma = rgb - l
    cmax = np.abs(chroma).max(axis=1, keepdims=True)
    k = 1.0 + amount * (1.0 - np.clip(cmax * 2.0, 0, 1))
    return l + chroma * k


def split_tone(rgb, shadow=(0, 0, 0), highlight=(0, 0, 0), balance=0.5, power=1.6):
    """Additive shadow/highlight tint, luma-weighted. Amounts ~0.00-0.08."""
    l = np.clip(luma(rgb), 0, 1)
    ls = np.clip((balance - l) / max(balance, 1e-6), 0, 1) ** power
    lh = np.clip((l - balance) / max(1 - balance, 1e-6), 0, 1) ** power
    return rgb + ls[:, None] * np.asarray(shadow, float) + lh[:, None] * np.asarray(highlight, float)


def channel_curve(rgb, r=None, g=None, b=None):
    """Per-channel monotone piecewise-linear curve. Each arg: [(in,out),...]."""
    out = rgb.copy()
    for i, pts in enumerate((r, g, b)):
        if not pts:
            continue
        xs = np.array([p[0] for p in pts], float)
        ys = np.array([p[1] for p in pts], float)
        out[:, i] = np.interp(rgb[:, i], xs, ys)
    return out


def print_black(rgb, black=0.0, white=1.0):
    """Compress output range: faded-film milk in the blacks, rolled highlights."""
    return black + rgb * (white - black)


def temperature(rgb, kelvin_shift=0.0, tint=0.0):
    """Crude but stable white-balance push. +shift = warmer. tint: + = magenta."""
    m = np.array([1.0 + 0.35 * kelvin_shift,
                  1.0 + 0.10 * tint,
                  1.0 - 0.35 * kelvin_shift])
    return np.clip(rgb * m, 0, 1)


def bw(rgb, weights, toning=(0, 0, 0)):
    """Panchromatic B&W conversion done in LINEAR light, then optional tone."""
    lin = srgb_to_lin(rgb)
    y = lin @ np.asarray(weights, float)
    grey = lin_to_srgb(np.repeat(y[:, None], 3, axis=1))
    if any(toning):
        grey = split_tone(grey, shadow=toning, highlight=tuple(-0.6 * t for t in toning))
    return grey


def cineon_to_lin(x, black=95.0, white=685.0, density=0.6, gamma=1.0):
    """Standard Cineon/DPX 10-bit log -> scene-linear (relative)."""
    code = np.clip(x, 0, 1) * 1023.0
    off = 10.0 ** ((black - white) * 0.002 / density)
    lin = (10.0 ** ((code - white) * 0.002 / density) - off) / (1.0 - off)
    return np.clip(lin, 0, None) ** gamma


# ---------------------------------------------------------------- writer

def make_grid(n):
    """(n^3, 3) grid with RED varying fastest — matches .cube data order."""
    ax = np.linspace(0.0, 1.0, n)
    b, g, r = np.meshgrid(ax, ax, ax, indexing="ij")
    return np.stack([r.ravel(), g.ravel(), b.ravel()], axis=1)


def write_cube(path, title, fn, size=33, clamp=True):
    grid = make_grid(size)
    out = np.asarray(fn(grid), float)
    if out.shape != grid.shape:
        raise ValueError(f"{title}: look returned {out.shape}, expected {grid.shape}")
    if not np.isfinite(out).all():
        raise ValueError(f"{title}: non-finite values in output")
    if clamp:
        out = np.clip(out, 0.0, 1.0)
    with open(path, "w") as f:
        f.write(f'TITLE "{title}"\n')
        f.write(f"LUT_3D_SIZE {size}\n")
        f.write("DOMAIN_MIN 0.0 0.0 0.0\n")
        f.write("DOMAIN_MAX 1.0 1.0 1.0\n\n")
        for row in out:
            f.write("%.6f %.6f %.6f\n" % (row[0], row[1], row[2]))
    return path


# ---------------------------------------------------------------- the looks

def look_apx100(rgb):
    """B&W, panchromatic response w/ mild red bias, medium contrast, cool-neutral.
    Approximates the *rendering* of a slow ISO100 B&W stock, not measured data."""
    x = bw(rgb, weights=(0.32, 0.53, 0.15))
    x = s_curve(x, 0.42, pivot=0.44)
    x = channel_curve(x,
                      r=[(0, .02), (.25, .24), (.75, .78), (1, .99)],
                      g=[(0, .02), (.25, .24), (.75, .78), (1, .99)],
                      b=[(0, .02), (.25, .24), (.75, .78), (1, .99)])
    return split_tone(x, shadow=(-0.004, 0.0, 0.010), highlight=(0.006, 0.004, 0.0))


def look_bw_redfilter(rgb):
    """B&W as if shot through a #25 red filter: dark skies, luminous skin."""
    x = bw(rgb, weights=(0.72, 0.26, 0.02))
    x = s_curve(x, 0.62, pivot=0.42)
    return print_black(x, 0.012, 0.995)


def look_portra_ish(rgb):
    """Warm negative-film look: creamy skin, soft cyan shadows, low contrast."""
    x = temperature(rgb, 0.030, 0.010)
    x = channel_curve(x,
                      r=[(0, .035), (.20, .215), (.55, .575), (.85, .875), (1, .985)],
                      g=[(0, .028), (.20, .200), (.55, .555), (.85, .860), (1, .975)],
                      b=[(0, .055), (.20, .195), (.55, .530), (.85, .830), (1, .950)])
    x = s_curve(x, 0.18, pivot=0.46)
    x = vibrance(x, 0.10)
    x = saturation(x, 0.96)
    return split_tone(x, shadow=(0.0, 0.006, 0.014), highlight=(0.012, 0.005, -0.006))


def look_teal_orange(rgb):
    """Blockbuster grade: teal shadows, orange mids/skin, punchy contrast."""
    x = s_curve(rgb, 0.55, pivot=0.42)
    x = lift_gamma_gain(x,
                        lift=(-0.006, 0.004, 0.020),
                        gamma=(1.03, 1.00, 0.97),
                        gain=(1.03, 1.00, 0.98))
    x = split_tone(x, shadow=(-0.012, 0.012, 0.045),
                   highlight=(0.030, 0.008, -0.022), balance=0.48, power=1.4)
    x = vibrance(x, 0.22)
    return np.clip(x, 0, 1)


def look_bleach_bypass(rgb):
    """Silver-retained look: crushed contrast, low sat, metallic highlights."""
    x = s_curve(rgb, 0.85, pivot=0.44)
    x = saturation(x, 0.42)
    x = lift_gamma_gain(x, lift=(0.010, 0.012, 0.016), gamma=(0.97, 0.97, 0.98))
    return split_tone(x, shadow=(0.0, 0.004, 0.010), highlight=(0.010, 0.010, 0.006))


def look_cross_process(rgb):
    """C-41 in E-6: cyan/green shadows, yellow highlights, blown blue channel."""
    x = channel_curve(rgb,
                      r=[(0, .02), (.25, .20), (.60, .68), (1, 1.0)],
                      g=[(0, .04), (.25, .26), (.60, .62), (1, .97)],
                      b=[(0, .14), (.35, .30), (.70, .60), (1, .88)])
    x = s_curve(x, 0.30, pivot=0.45)
    x = vibrance(x, 0.30)
    return np.clip(x, 0, 1)


def look_faded_matte(rgb):
    """Low-contrast matte: lifted milky blacks, rolled highlights, dusty warmth."""
    x = print_black(rgb, 0.075, 0.945)
    x = channel_curve(x,
                      r=[(0, .085), (.5, .515), (1, .950)],
                      g=[(0, .078), (.5, .500), (1, .940)],
                      b=[(0, .090), (.5, .490), (1, .920)])
    x = saturation(x, 0.88)
    return split_tone(x, shadow=(0.010, 0.004, 0.006), highlight=(0.008, 0.004, -0.004))


def look_night(rgb):
    """Day-for-night: heavy blue bias, dark mids, protected highlights."""
    lin = srgb_to_lin(rgb) * 0.42
    x = lin_to_srgb(lin)
    x = temperature(x, -0.075, -0.020)
    x = s_curve(x, 0.35, pivot=0.35)
    x = saturation(x, 0.72)
    return split_tone(x, shadow=(-0.004, 0.0, 0.030), highlight=(0.0, 0.006, 0.020))


def look_neutral_contrast(rgb):
    """Utility: pure filmic contrast, zero hue shift. Good base to stack under."""
    return s_curve(rgb, 0.45, pivot=0.435)


def look_cineon_rec709(rgb):
    """Technical: Cineon/DPX log -> Rec.709 display, with a film-print S-curve."""
    lin = cineon_to_lin(rgb)
    x = lin_to_srgb(np.clip(lin * 0.85, 0, 1))
    x = s_curve(x, 0.30, pivot=0.42)
    return np.clip(x, 0, 1)


LOOKS = [
    ("agfa_apx_100_emulation", "Agfa APX 100 (B&W emulation)", look_apx100),
    ("bw_red_filter_25", "B&W Red Filter #25", look_bw_redfilter),
    ("portra_warm_negative", "Warm Negative (Portra-ish)", look_portra_ish),
    ("teal_and_orange", "Teal & Orange Cine", look_teal_orange),
    ("bleach_bypass", "Bleach Bypass", look_bleach_bypass),
    ("cross_process", "Cross Process", look_cross_process),
    ("faded_matte", "Faded Matte", look_faded_matte),
    ("day_for_night", "Day for Night", look_night),
    ("neutral_filmic_contrast", "Neutral Filmic Contrast", look_neutral_contrast),
    ("cineon_log_to_rec709", "Cineon Log to Rec.709", look_cineon_rec709),
]


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else "luts"
    size = int(os.environ.get("LUT_SIZE", "33"))
    os.makedirs(outdir, exist_ok=True)
    for slug, title, fn in LOOKS:
        p = write_cube(os.path.join(outdir, f"{slug}.cube"), title, fn, size=size)
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
