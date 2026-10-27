#!/usr/bin/env python3
"""Render the README illustrations.

These are hand-drawn mockups (not screenshots) of the GNOME top bar menu and
the GTK4 app window, so the repository does not ship pictures of a real desktop.

    python3 docs/render-mockups.py
"""

import math
import os

import cairo
import gi

gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Pango, PangoCairo  # noqa: E402

SCALE = 2

# Adwaita dark-ish palette
PANEL = (0.05, 0.05, 0.06, 0.72)
MENU_BG = (0.145, 0.145, 0.16, 0.98)
MENU_BORDER = (1, 1, 1, 0.10)
ROW_HOVER = (1, 1, 1, 0.06)
TEXT = (1, 1, 1, 0.92)
TEXT_DIM = (1, 1, 1, 0.55)
ACCENT = (0.208, 0.518, 0.894, 1)
RED = (0.878, 0.106, 0.141, 1)
SEP = (1, 1, 1, 0.10)


def rounded(cr, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


def text(cr, x, y, value, size=12.5, color=TEXT, weight=Pango.Weight.NORMAL,
         align="left", width=None):
    layout = PangoCairo.create_layout(cr)
    desc = Pango.FontDescription("Cantarell")
    desc.set_absolute_size(size * Pango.SCALE)
    desc.set_weight(weight)
    layout.set_font_description(desc)
    layout.set_text(value, -1)
    if width is not None:
        layout.set_width(int(width * Pango.SCALE))
        layout.set_ellipsize(Pango.EllipsizeMode.END)
    if align == "right":
        layout.set_alignment(Pango.Alignment.RIGHT)
    elif align == "center":
        layout.set_alignment(Pango.Alignment.CENTER)

    w, h = layout.get_pixel_size()
    cr.set_source_rgba(*color)
    cr.move_to(x, y - h / 2)  # y is the vertical centre
    PangoCairo.show_layout(cr, layout)
    return w, h


def measure(cr, value, size=12.5, weight=Pango.Weight.NORMAL):
    layout = PangoCairo.create_layout(cr)
    desc = Pango.FontDescription("Cantarell")
    desc.set_absolute_size(size * Pango.SCALE)
    desc.set_weight(weight)
    layout.set_font_description(desc)
    layout.set_text(value, -1)
    return layout.get_pixel_size()


def shadow(cr, x, y, w, h, r):
    for i in range(6, 0, -1):
        cr.set_source_rgba(0, 0, 0, 0.05)
        rounded(cr, x - i, y - i + 2, w + 2 * i, h + 2 * i, r + i)
        cr.fill()


def wallpaper(cr, w, h):
    grad = cairo.LinearGradient(0, 0, w, h)
    grad.add_color_stop_rgb(0.0, 0.10, 0.14, 0.22)
    grad.add_color_stop_rgb(0.5, 0.09, 0.20, 0.27)
    grad.add_color_stop_rgb(1.0, 0.16, 0.10, 0.20)
    cr.set_source(grad)
    cr.paint()

    glow = cairo.RadialGradient(w * 0.75, h * 0.3, 10, w * 0.75, h * 0.3, w * 0.7)
    glow.add_color_stop_rgba(0, 0.35, 0.55, 0.85, 0.35)
    glow.add_color_stop_rgba(1, 0.0, 0.0, 0.0, 0)
    cr.set_source(glow)
    cr.paint()


# --------------------------------------------------------------------- icons
def icon_wifi(cr, x, y, s, alpha=0.92):
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_line_width(1.6)
    cr.set_source_rgba(1, 1, 1, alpha)
    for r in (s * 0.62, s * 0.40, s * 0.18):
        cr.new_sub_path()
        cr.arc(x, y + s * 0.34, r, -2.30, -0.84)
        cr.stroke()
    cr.new_sub_path()
    cr.arc(x, y + s * 0.34, 1.3, 0, 2 * math.pi)
    cr.fill()


def icon_volume(cr, x, y, s, alpha=0.92):
    cr.set_source_rgba(1, 1, 1, alpha)
    cr.new_sub_path()
    cr.move_to(x - s * 0.45, y - s * 0.18)
    cr.line_to(x - s * 0.18, y - s * 0.18)
    cr.line_to(x + s * 0.1, y - s * 0.45)
    cr.line_to(x + s * 0.1, y + s * 0.45)
    cr.line_to(x - s * 0.18, y + s * 0.18)
    cr.line_to(x - s * 0.45, y + s * 0.18)
    cr.close_path()
    cr.fill()
    cr.set_line_width(1.5)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.new_sub_path()
    cr.arc(x + s * 0.12, y, s * 0.34, -0.9, 0.9)
    cr.stroke()


def icon_battery(cr, x, y, s, alpha=0.92):
    cr.set_source_rgba(1, 1, 1, alpha)
    cr.set_line_width(1.4)
    cr.new_sub_path()
    rounded(cr, x - s * 0.5, y - s * 0.26, s * 0.9, s * 0.52, 2.2)
    cr.stroke()
    cr.new_sub_path()
    cr.rectangle(x + s * 0.44, y - s * 0.1, s * 0.1, s * 0.2)
    cr.fill()
    cr.new_sub_path()
    cr.rectangle(x - s * 0.40, y - s * 0.16, s * 0.55, s * 0.32)
    cr.fill()


def icon_display(cr, x, y, s, color=(1, 1, 1, 0.95)):
    cr.set_source_rgba(*color)
    cr.set_line_width(1.5)
    cr.new_sub_path()
    rounded(cr, x - s * 0.5, y - s * 0.36, s, s * 0.66, 2.0)
    cr.stroke()
    cr.set_line_width(1.5)
    cr.move_to(x - s * 0.16, y + s * 0.30)
    cr.line_to(x - s * 0.16, y + s * 0.46)
    cr.move_to(x + s * 0.16, y + s * 0.30)
    cr.line_to(x + s * 0.16, y + s * 0.46)
    cr.move_to(x - s * 0.32, y + s * 0.46)
    cr.line_to(x + s * 0.32, y + s * 0.46)
    cr.stroke()


def icon_record(cr, x, y, r, color=RED):
    cr.set_source_rgba(*color)
    cr.new_sub_path()
    cr.arc(x, y, r, 0, 2 * math.pi)
    cr.fill()


def chevron(cr, x, y, size=4.2, color=TEXT_DIM, direction="right"):
    cr.set_source_rgba(*color)
    cr.set_line_width(1.5)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.new_sub_path()
    if direction == "down":
        cr.move_to(x - size, y - size / 2)
        cr.line_to(x, y + size)
        cr.line_to(x + size, y - size / 2)
    elif direction == "right":
        cr.move_to(x - size / 2, y - size)
        cr.line_to(x + size / 2, y)
        cr.line_to(x - size / 2, y + size)
    else:  # up
        cr.move_to(x - size, y + size / 2)
        cr.line_to(x, y - size / 2)
        cr.line_to(x + size, y + size / 2)
    cr.stroke()


# ---------------------------------------------------------------- top bar art
def menu_row(cr, x, y, w, label, h=34, dot=False, chev=None, dim=False,
             bold=False, indent=0):
    if dot:
        cr.set_source_rgba(1, 1, 1, 0.9)
        cr.arc(x + 15 + indent, y + h / 2, 2.6, 0, 2 * math.pi)
        cr.fill()
    text(cr, x + 30 + indent, y + h / 2, label,
         size=12 if not bold else 12.5,
         color=TEXT_DIM if dim else TEXT,
         weight=Pango.Weight.BOLD if bold else Pango.Weight.NORMAL)
    if chev:
        chevron(cr, x + w - 18, y + h / 2, direction=chev)


def separator(cr, x, y, w):
    cr.set_source_rgba(*SEP)
    cr.rectangle(x + 12, y, w - 24, 1)
    cr.fill()


def render_topbar(path):
    W, H = 840, 400
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, W * SCALE, H * SCALE)
    cr = cairo.Context(surface)
    cr.scale(SCALE, SCALE)
    wallpaper(cr, W, H)

    # ---------------------------------------------------------------- panel
    cr.set_source_rgba(*PANEL)
    cr.rectangle(0, 0, W, 34)
    cr.fill()

    text(cr, 16, 17, "Activities", size=12.5, color=(1, 1, 1, 0.95))
    text(cr, W / 2, 17, "Tue 23:41", size=12.5, color=(1, 1, 1, 0.95),
         align="center")

    icon_wifi(cr, W - 232, 17, 13)
    icon_volume(cr, W - 202, 17, 13)
    icon_battery(cr, W - 172, 17, 13)

    # the feature: indicator, drawn like an open panel button
    cr.set_source_rgba(1, 1, 1, 0.14)
    rounded(cr, W - 146, 4, 40, 26, 8)
    cr.fill()
    icon_display(cr, W - 126, 17, 15)
    chevron(cr, W - 96, 17, size=3.2, color=(1, 1, 1, 0.9))

    # ---------------------------------------------------------------- menu
    rows = [
        ("status", "Not mirroring · 12 Mbps, 30 fps", 38),
        ("device", "Living Room · 192.168.1.169", 30),
        ("sep", None, 1),
        ("row", "Start mirroring", 34),
        ("row", "Pair with Apple TV…", 34),
        ("row", "Quality", 34),
        ("sep", None, 1),
        ("row", "Set Apple TV address…", 34),
    ]

    menu_w = 392
    menu_x = W - menu_w - 18
    menu_y = 44
    pad = 8
    menu_h = sum(h for _, _, h in rows) + 2 * pad

    shadow(cr, menu_x, menu_y, menu_w, menu_h, 14)
    cr.set_source_rgba(*MENU_BG)
    rounded(cr, menu_x, menu_y, menu_w, menu_h, 14)
    cr.fill_preserve()
    cr.set_source_rgba(*MENU_BORDER)
    cr.set_line_width(1)
    cr.stroke()

    y = menu_y + pad
    quality_y = None
    hover = None
    for kind, label, h in rows:
        if kind == "status":
            text(cr, menu_x + 16, y + 13, label, size=12.5,
                 weight=Pango.Weight.BOLD)
        elif kind == "device":
            text(cr, menu_x + 16, y + 12, label, size=11, color=TEXT_DIM)
        elif kind == "sep":
            separator(cr, menu_x, y, menu_w)
        else:
            menu_row(cr, menu_x, y, menu_w, label, h=h,
                     chev="right" if label == "Quality" else None)
            if label == "Quality":
                quality_y = y
            if label == "Start mirroring":
                hover = y
        y += h

    if hover is not None:
        cr.set_source_rgba(*ROW_HOVER)
        rounded(cr, menu_x + 6, hover + 1, menu_w - 12, 32, 8)
        cr.fill()

    # ------------------------------------------------------- quality submenu
    sub_rows = [
        ("dot", "High — 12 Mbps", 34),
        ("plain", "Balanced — 8 Mbps", 34),
        ("plain", "Data saver — 4 Mbps", 34),
        ("sep", None, 1),
        ("dot", "30 fps", 34),
        ("plain", "60 fps", 34),
    ]
    sub_w = 300
    sub_x = menu_x - sub_w - 10
    sub_y = quality_y - 6
    sub_h = sum(h for _, _, h in sub_rows) + 2 * pad

    shadow(cr, sub_x, sub_y, sub_w, sub_h, 14)
    cr.set_source_rgba(*MENU_BG)
    rounded(cr, sub_x, sub_y, sub_w, sub_h, 14)
    cr.fill_preserve()
    cr.set_source_rgba(*MENU_BORDER)
    cr.set_line_width(1)
    cr.stroke()

    y = sub_y + pad
    for kind, label, h in sub_rows:
        if kind == "sep":
            separator(cr, sub_x, y, sub_w)
        else:
            menu_row(cr, sub_x, y, sub_w, label, h=h, dot=(kind == "dot"))
        y += h

    surface.write_to_png(path)
    print("wrote", path)


# ---------------------------------------------------------------- app window
def render_app(path):
    win_w = 470
    win_x_pad = 100
    content_h = 46 + 28 + 62 + 44 + 12 + 38 + 26 + 18 + 44 * 3 + 24 + 40 + 30
    win_h = content_h
    W, H = win_w + win_x_pad * 2, win_h + 130

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, W * SCALE, H * SCALE)
    cr = cairo.Context(surface)
    cr.scale(SCALE, SCALE)
    wallpaper(cr, W, H)
    cr.set_source_rgba(0, 0, 0, 0.45)
    cr.paint()

    win_x, win_y = win_x_pad, (H - win_h) / 2

    shadow(cr, win_x, win_y, win_w, win_h, 14)
    cr.set_source_rgba(0.14, 0.14, 0.155, 1)
    rounded(cr, win_x, win_y, win_w, win_h, 14)
    cr.fill()

    cr.save()
    rounded(cr, win_x, win_y, win_w, win_h, 14)
    cr.clip()
    cr.set_source_rgba(0.19, 0.19, 0.205, 1)
    cr.rectangle(win_x, win_y, win_w, 46)
    cr.fill()
    cr.set_source_rgba(*SEP)
    cr.rectangle(win_x, win_y + 45, win_w, 1)
    cr.fill()

    text(cr, win_x + win_w / 2, win_y + 23, "Doubletake", size=12.5,
         weight=Pango.Weight.BOLD, align="center")
    cr.set_source_rgba(1, 1, 1, 0.10)
    rounded(cr, win_x + 10, win_y + 11, 66, 24, 8)
    cr.fill()
    for i in range(3):
        cr.new_sub_path()
        cr.set_source_rgba(1, 1, 1, 0.35)
        cr.arc(win_x + 24 + i * 18, win_y + 23, 3.2, 0, 2 * math.pi)
        cr.fill()

    cx = win_x + 28
    cy = win_y + 46 + 28

    text(cr, cx, cy, "Not mirroring", size=23, weight=Pango.Weight.BOLD)
    text(cr, cx, cy + 28, "Living Room · 192.168.1.169", size=11.5,
         color=TEXT_DIM)
    cy += 62

    cr.set_source_rgba(*ACCENT)
    rounded(cr, cx, cy, win_w - 56, 44, 22)
    cr.fill()
    text(cr, cx + (win_w - 56) / 2, cy + 22, "Start mirroring", size=12.5,
         weight=Pango.Weight.BOLD, align="center", color=(1, 1, 1, 1))
    cy += 44 + 12

    cr.set_source_rgba(1, 1, 1, 0.10)
    rounded(cr, cx, cy, win_w - 56, 38, 8)
    cr.fill()
    text(cr, cx + (win_w - 56) / 2, cy + 19, "Pair with Apple TV…", size=12.5,
         align="center")
    cy += 38 + 26

    text(cr, cx, cy, "Quality", size=11, color=TEXT_DIM,
         weight=Pango.Weight.BOLD)
    cy += 18

    group_w = win_w - 56
    rows = [("Bitrate", "12 Mbps"), ("Frame rate", "30 fps")]
    cr.set_source_rgba(1, 1, 1, 0.055)
    rounded(cr, cx, cy, group_w, 44 * len(rows) + 44, 10)
    cr.fill()

    for i, (label, value) in enumerate(rows):
        ry = cy + i * 44
        text(cr, cx + 14, ry + 22, label, size=12.5)
        vw = measure(cr, value, size=12.5)[0]
        text(cr, cx + group_w - 14 - vw - 16, ry + 22, value, size=12.5,
             color=TEXT_DIM)
        chevron(cr, cx + group_w - 18, ry + 22, size=3.2, direction="down")
        if i:
            cr.set_source_rgba(*SEP)
            cr.rectangle(cx + 12, ry, group_w - 24, 1)
            cr.fill()

    ry = cy + 44 * len(rows)
    cr.set_source_rgba(*SEP)
    cr.rectangle(cx + 12, ry, group_w - 24, 1)
    cr.fill()
    text(cr, cx + 14, ry + 22, "Apple TV address", size=12.5)
    vw = measure(cr, "192.168.1.169", size=12.5)[0]
    text(cr, cx + group_w - 14 - vw, ry + 22, "192.168.1.169", size=12.5,
         color=TEXT_DIM)
    cy += 44 * len(rows) + 44 + 24

    cr.set_source_rgba(1, 1, 1, 0.055)
    rounded(cr, cx, cy, group_w, 40, 10)
    cr.fill()
    text(cr, cx + 14, cy + 20, "Log", size=12.5, color=TEXT_DIM)
    chevron(cr, cx + group_w - 20, cy + 20, size=3.2)
    cr.restore()

    surface.write_to_png(path)
    print("wrote", path)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    render_topbar(os.path.join(here, "topbar.png"))
    render_app(os.path.join(here, "app.png"))
