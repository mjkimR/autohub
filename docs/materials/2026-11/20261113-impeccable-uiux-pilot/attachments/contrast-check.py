import math


def oklch_to_lin(L, C, h):
    a = C * math.cos(math.radians(h))
    b = C * math.sin(math.radians(h))
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    lc, mc, sc = l_**3, m_**3, s_**3
    r = 4.0767416621 * lc - 3.3077115913 * mc + 0.2309699292 * sc
    g = -1.2684380046 * lc + 2.6097574011 * mc - 0.3413193965 * sc
    bb = -0.0041960863 * lc - 0.7034186147 * mc + 1.7076147010 * sc
    return [min(1, max(0, x)) for x in (r, g, bb)]


def enc(x):
    return 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055


def dec(x):
    return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4


def srgb(c):
    return [enc(x) for x in oklch_to_lin(*c)]


def mix(fg, a, bg):  # alpha composite in sRGB
    f = srgb(fg) if isinstance(fg, tuple) else fg
    b = srgb(bg) if isinstance(bg, tuple) else bg
    return [a * x + (1 - a) * y for x, y in zip(f, b, strict=True)]


def lum(rgb):
    r, g, b = [dec(x) for x in rgb]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def cr(a, b):
    a = srgb(a) if isinstance(a, tuple) else a
    b = srgb(b) if isinstance(b, tuple) else b
    la, lb = sorted([lum(a), lum(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


T = {
    "light": dict(
        bg=(0.985, 0, 0),
        card=(1, 0, 0),
        fg=(0.17, 0.005, 260),
        muted=(0.955, 0, 0),
        mfg=(0.50, 0, 0),
        primary=(0.24, 0.012, 260),
        pfg=(0.985, 0, 0),
        ring=(0.45, 0.01, 260),
        destructive=(0.53, 0.19, 27),
        success=(0.50, 0.07, 160),
        info=(0.50, 0.035, 250),
        warning=(0.50, 0.08, 80),
        attention=(0.78, 0.165, 70),
        afg=(0.20, 0.04, 55),
        atext=(0.50, 0.13, 55),
        asurf=(0.97, 0.04, 80),
        sidebar=(0.975, 0, 0),
        saccent=(0.93, 0, 0),
    ),
    "dark": dict(
        bg=(0.155, 0, 0),
        card=(0.19, 0, 0),
        fg=(0.96, 0, 0),
        muted=(0.22, 0, 0),
        mfg=(0.72, 0, 0),
        primary=(0.93, 0.005, 260),
        pfg=(0.17, 0.005, 260),
        ring=(0.75, 0.005, 260),
        destructive=(0.68, 0.17, 25),
        success=(0.74, 0.07, 160),
        info=(0.74, 0.035, 250),
        warning=(0.76, 0.07, 85),
        attention=(0.82, 0.16, 75),
        afg=(0.19, 0.04, 55),
        atext=(0.82, 0.16, 75),
        asurf=(0.24, 0.05, 70),
        sidebar=(0.17, 0, 0),
        saccent=(0.24, 0, 0),
    ),
}
for mode, t in T.items():
    print("==", mode)
    rows = [
        ("text fg/bg", t["fg"], t["bg"], 4.5),
        ("text fg/card", t["fg"], t["card"], 4.5),
        ("text muted-fg/bg", t["mfg"], t["bg"], 4.5),
        ("text muted-fg/card", t["mfg"], t["card"], 4.5),
        ("text muted-fg/muted", t["mfg"], t["muted"], 4.5),
        ("text primary-fg/primary", t["pfg"], t["primary"], 4.5),
        ("text attention-fg/attention", t["afg"], t["attention"], 4.5),
        ("text attention-text/card", t["atext"], t["card"], 4.5),
        ("text attention-text/bg", t["atext"], t["bg"], 4.5),
        ("text attention-text/attention-surface", t["atext"], t["asurf"], 4.5),
        ("text fg/attention-surface", t["fg"], t["asurf"], 4.5),
        ("text fg/sidebar-accent", t["fg"], t["saccent"], 4.5),
        ("ui attention/card", t["attention"], t["card"], 3),
        ("ui attention/bg", t["attention"], t["bg"], 3),
        ("ui ring/bg", t["ring"], t["bg"], 3),
        ("ui primary/bg", t["primary"], t["bg"], 3),
    ]
    for k in ["destructive", "success", "info", "warning"]:
        rows.append((f"text {k}/card", t[k], t["card"], 4.5))
        a = 0.10 if k == "destructive" else 0.15
        if mode == "dark" and k == "destructive":
            a = 0.20
        rows.append((f"text {k}/{k}-tint{int(a * 100)} over card", t[k], mix(t[k], a, t["card"]), 4.5))
        rows.append((f"text {k}/{k}-tint over bg", t[k], mix(t[k], a, t["bg"]), 4.5))
    rows.append(
        ("text attention-text/attention-tint15 over card", t["atext"], mix(t["attention"], 0.15, t["card"]), 4.5)
    )
    for n, a, b, th in rows:
        c = cr(a, b)
        print(f"{'OK ' if c >= th else 'FAIL'} {c:5.2f} (>= {th}) {n}")
for c in [(0.24, 0.012, 260), (0.93, 0.005, 260)]:
    print(c, "#" + "".join(f"{round(x * 255):02x}" for x in srgb(c)))
print("sidebar-accent vs sidebar light", cr((0.93, 0, 0), (0.975, 0, 0)), "dark", cr((0.24, 0, 0), (0.17, 0, 0)))
