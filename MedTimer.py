"""
MedTimer - Your Daily Medicine Companion  (single-file Streamlit app)

Run:        pip install streamlit pandas pillow
            streamlit run MedTimer.py

Everything lives in this ONE file: database, scheduling logic, reminders, reports, the Turtle-graphics
badge, Pilly's artwork (drawn from code as SVG) and every screen. The whole app runs on a single Streamlit
page: navigation is st.session_state + conditional rendering, so there are no links, new tabs or redirects.
Data lives in a SQLite file inside a fresh temporary folder created each time the app process starts, so a
restart always begins with the welcome / set-up screens. The sections below are the app's modules, embedded as
source text and loaded at start-up so the file stays self-contained; the entry point is at the very bottom.
"""
import atexit
import hashlib
import linecache
import os
import shutil
import sys
import tempfile
import types

import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))

# =====================================================================================================
#  EMBEDDED MODULES
# =====================================================================================================
MODULES = [
('config', r'''"""Shared constants: palette, paths, defaults."""
import os

# Palette (ivory / navy / sage / antique gold)
IVORY = "#FBF7EC"
IVORY_D = "#F3ECD9"
CARD = "#FFFEF9"
NAVY = "#1E3A5F"
NAVY_D = "#13263F"
NAVY_L = "#3F6CA3"
SAGE = "#7FA17B"
SAGE_L = "#DCE8D6"
GOLD = "#B8903A"
GOLD_L = "#F3E6BE"
TEXT = "#2B3A4A"
MUTED = "#667487"
BORDER = "#E2D9C2"
GREEN = "#2E8B45"        # status colour: TAKEN
GREEN_L = "#DCF2DC"
AMBER = "#E0A800"        # status colour: UPCOMING (yellow)
AMBER_L = "#FFF1B0"
RED = "#C8372D"          # status colour: MISSED
RED_L = "#F9D9D5"

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAYS_LONG = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSET_DIR = os.path.join(ROOT, "assets")
PILLY_DIR = os.path.join(ASSET_DIR, "pilly")
GEN_DIR = os.path.join(ASSET_DIR, "generated")

# The entry point points these at a brand-new temporary folder every time the app process starts (see
# _fresh_data_home at the bottom), so nothing entered in an earlier run is ever loaded again.
DATA_DIR = ""
DB_PATH = ""

DEFAULT_SETTINGS = {
    "reminders_enabled": "1",   # master switch for automatic reminders
    "popup": "1",               # show the Pilly pop-up
    "banner": "1",              # show 'due now' banner on dashboard
    "audio": "1",               # play a sound with reminders
    "sound": "chime",           # chime | bell | ding
    "volume": "70",             # 0-100
    "snooze_default": "10",     # minutes
    "window": "60",             # minutes a dose counts as 'due' before it is shown as missed
    "h24": "0",                 # 24-hour display
}
SNOOZE_CHOICES = [5, 10, 15, 20, 30]   # presets; users can also type their own number of minutes
SNOOZE_MIN, SNOOZE_MAX = 1, 180        # allowed custom snooze length (minutes)
WINDOW_CHOICES = [15, 30, 45, 60, 90, 120]
SOUNDS = {"chime": "Soft chime", "bell": "Little bell", "ding": "Double ding"}

DISCLAIMER = ("MedTimer is a medicine tracking and reminder app. It does not give medical advice and does not "
              "replace your doctor, nurse or pharmacist. Enter schedules exactly as your healthcare professional "
              "told you.")
'''),
('pilly_art', r'''"""
Pilly artwork generator.

Pilly is ONE capsule character: navy upper half, ivory lower half, a white doctor's
coat (open at the front so the capsule shape stays visible) and a stethoscope.
Every pose is produced by the same functions, so the body, coat, stethoscope and
face are identical in every image; only arms, legs, eyes, mouth and props change.

Run this file directly to (re)generate the PNG/SVG assets into assets/pilly/:
    python -m medtimer.pilly_art
PNG export uses `rsvg-convert` if it is installed, otherwise the optional
`cairosvg` package. The generated PNGs are committed with the project, so the
app itself never needs either tool.
"""
import math
import os
import random
import shutil
import subprocess

W, H = 480, 560
POSES = ["welcome", "reminder", "completed", "progress", "achievement", "tips", "thumbsup"]

NAVY, NAVY_D, IVORY = "#1E3A5F", "#0E2342", "#FBF3E0"
GOLD, GOLD_D, SAGE = "#C9A24A", "#9C7A2E", "#8FAE8B"


def _star(cx, cy, r, fill=GOLD, op=1.0):
    k = r * 0.28
    pts = [(cx, cy - r), (cx + k, cy - k), (cx + r, cy), (cx + k, cy + k),
           (cx, cy + r), (cx - k, cy + k), (cx - r, cy), (cx - k, cy - k)]
    d = "M" + " L".join("%.1f %.1f" % p for p in pts) + " Z"
    return '<path d="%s" fill="%s" opacity="%s"/>' % (d, fill, op)


def _defs():
    return """
<defs>
  <radialGradient id="navyG" cx="32%" cy="22%" r="85%">
    <stop offset="0" stop-color="#5B86BD"/><stop offset=".38" stop-color="#25497C"/>
    <stop offset="1" stop-color="#0E2342"/></radialGradient>
  <radialGradient id="ivoryG" cx="34%" cy="30%" r="90%">
    <stop offset="0" stop-color="#FFFFFB"/><stop offset=".5" stop-color="#F6EBD0"/>
    <stop offset="1" stop-color="#D6C4A0"/></radialGradient>
  <linearGradient id="cylG" x1="0" x2="1" y1="0" y2="0">
    <stop offset="0" stop-color="#000" stop-opacity=".30"/><stop offset=".22" stop-color="#000" stop-opacity="0"/>
    <stop offset=".72" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".34"/></linearGradient>
  <linearGradient id="glossG" x1="0" x2="0" y1="0" y2="1">
    <stop offset="0" stop-color="#fff" stop-opacity=".55"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
  <linearGradient id="coatG" x1="0" x2="1" y1="0" y2="1">
    <stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#DCE3EC"/></linearGradient>
  <linearGradient id="coatG2" x1="1" x2="0" y1="0" y2="1">
    <stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#DCE3EC"/></linearGradient>
  <radialGradient id="metalG" cx="35%" cy="30%" r="80%">
    <stop offset="0" stop-color="#FFFFFF"/><stop offset=".5" stop-color="#BCC5D0"/>
    <stop offset="1" stop-color="#6F7986"/></radialGradient>
  <radialGradient id="handG" cx="35%" cy="30%" r="80%">
    <stop offset="0" stop-color="#FFFFFF"/><stop offset=".6" stop-color="#F7EBD1"/>
    <stop offset="1" stop-color="#DCC9A0"/></radialGradient>
  <radialGradient id="shadowG" cx="50%" cy="50%" r="50%">
    <stop offset="0" stop-color="#3a3224" stop-opacity=".38"/><stop offset="1" stop-color="#3a3224" stop-opacity="0"/></radialGradient>
  <clipPath id="capsuleClip"><rect x="125" y="80" width="150" height="330" rx="75" ry="75"/></clipPath>
</defs>"""


def _body():
    return """
<g id="body">
  <g clip-path="url(#capsuleClip)">
    <rect x="125" y="80" width="150" height="178" fill="url(#navyG)"/>
    <rect x="125" y="258" width="150" height="152" fill="url(#ivoryG)"/>
    <rect x="125" y="80" width="150" height="330" fill="url(#cylG)"/>
    <rect x="125" y="254" width="150" height="8" fill="#0A1A33" opacity=".35"/>
    <rect x="125" y="262" width="150" height="3" fill="#fff" opacity=".55"/>
    <rect x="146" y="108" width="15" height="92" rx="7.5" fill="url(#glossG)" transform="rotate(8 153 154)"/>
    <rect x="146" y="298" width="9" height="62" rx="4.5" fill="#fff" opacity=".6"/>
  </g>
  <rect x="125" y="80" width="150" height="330" rx="75" ry="75" fill="none" stroke="#10264A" stroke-width="2.2"/>
</g>"""


def _face(mood):
    ex = (172, 228)
    ey = 176
    s = ['<g id="face">']
    for i, x in enumerate(ex):
        if mood == "happy":
            s.append('<path d="M%d %d Q%d %d %d %d" stroke="#FFFFFF" stroke-width="5" fill="none" stroke-linecap="round"/>'
                     % (x - 13, ey + 5, x, ey - 14, x + 13, ey + 5))
        else:
            px, py = (3, 0)
            if mood == "think":
                px, py = (4, -5)
            s.append('<ellipse cx="%d" cy="%d" rx="14" ry="17" fill="#FFFFFF" stroke="#0A1A33" stroke-width="1.5"/>' % (x, ey))
            s.append('<circle cx="%d" cy="%d" r="9" fill="#10203A"/>' % (x + px, ey + py + 1))
            s.append('<circle cx="%d" cy="%d" r="3.4" fill="#FFFFFF"/>' % (x + px + 3, ey + py - 3))
            s.append('<circle cx="%d" cy="%d" r="1.6" fill="#FFFFFF" opacity=".8"/>' % (x + px - 3, ey + py + 5))
    # brows
    lift = -6 if mood == "think" else 0
    s.append('<path d="M158 %d Q172 %d 186 %d" stroke="#9DB8DC" stroke-width="3" fill="none" stroke-linecap="round"/>'
             % (150 + lift, 143 + lift, 150 + lift))
    s.append('<path d="M214 150 Q228 143 242 150" stroke="#9DB8DC" stroke-width="3" fill="none" stroke-linecap="round"/>')
    # cheeks
    s.append('<ellipse cx="146" cy="208" rx="11" ry="6.5" fill="#F4A9A0" opacity=".55"/>')
    s.append('<ellipse cx="254" cy="208" rx="11" ry="6.5" fill="#F4A9A0" opacity=".55"/>')
    # mouth
    if mood == "think":
        s.append('<path d="M188 214 Q200 221 212 213" stroke="#FFEFD0" stroke-width="3.4" fill="none" stroke-linecap="round"/>')
    elif mood == "wow":
        s.append('<path d="M180 208 Q200 246 220 208 Z" fill="#7A1F2B" stroke="#FFEFD0" stroke-width="2" stroke-linejoin="round"/>'
                 '<ellipse cx="200" cy="226" rx="10" ry="5" fill="#E8828A"/>'
                 '<path d="M184 209 Q200 214 216 209" stroke="#FFFFFF" stroke-width="4" fill="none"/>')
    else:
        s.append('<path d="M184 208 Q200 234 216 208 Z" fill="#7A1F2B" stroke="#FFEFD0" stroke-width="2" stroke-linejoin="round"/>'
                 '<ellipse cx="200" cy="222" rx="8" ry="4" fill="#E8828A"/>'
                 '<path d="M188 209 Q200 213 212 209" stroke="#FFFFFF" stroke-width="3.4" fill="none"/>')
    s.append("</g>")
    return "".join(s)


def _glasses():
    return ('<g id="glasses" fill="#FFFFFF" fill-opacity=".14" stroke="%s" stroke-width="3.2">'
            '<circle cx="172" cy="176" r="21"/><circle cx="228" cy="176" r="21"/>'
            '<path d="M193 174 Q200 169 207 174" fill="none"/>'
            '<path d="M151 172 L135 166 M249 172 L265 166" fill="none" stroke-linecap="round"/>'
            '<path d="M160 163 Q166 158 174 160" stroke="#fff" stroke-opacity=".8" fill="none" stroke-width="2"/></g>' % GOLD)


def _coat():
    """White doctor's coat: two fitted panels hugging the sides, lapels, pocket, folds.
    The front is open wide so the navy/ivory capsule body stays instantly recognisable."""
    panel = ('<path d="M123 264 C115 298 112 346 118 390 Q142 402 168 394 L170 324 L160 288 Z" '
             'fill="url(#coatG)" stroke="#A9B6C7" stroke-width="2" stroke-linejoin="round"/>'
             '<path d="M126 322 Q139 334 135 356" stroke="#B7C2D1" stroke-width="2.2" fill="none" stroke-linecap="round"/>'
             '<path d="M122 350 Q133 360 130 380" stroke="#C3CCD9" stroke-width="2" fill="none" stroke-linecap="round"/>'
             '<path d="M150 366 Q157 380 154 394" stroke="#C3CCD9" stroke-width="2" fill="none" stroke-linecap="round"/>'
             '<path d="M164 330 Q168 360 166 392" stroke="#B7C2D1" stroke-width="2.2" fill="none" stroke-linecap="round"/>')
    left = '<g id="coatL">%s</g>' % panel
    right = ('<g id="coatR" transform="translate(400 0) scale(-1 1)">%s</g>' % panel).replace("url(#coatG)", "url(#coatG2)")
    pocket = ('<g id="pocket"><path d="M128 336 L156 336 L154 360 Q142 366 130 360 Z" fill="#F2F5F9" stroke="#A9B6C7" stroke-width="1.8"/>'
              '<path d="M142 342 v10 M137 347 h10" stroke="%s" stroke-width="3" stroke-linecap="round"/>'
              '<rect x="146" y="326" width="4" height="16" rx="2" fill="#2E4F7E"/></g>' % SAGE)
    lapels = ('<g id="lapels">'
              '<path d="M150 252 L176 296 L162 304 L138 268 Z" fill="#FFFFFF" stroke="#A9B6C7" stroke-width="2" stroke-linejoin="round"/>'
              '<path d="M250 252 L224 296 L238 304 L262 268 Z" fill="#FFFFFF" stroke="#A9B6C7" stroke-width="2" stroke-linejoin="round"/>'
              '<path d="M153 262 L172 292" stroke="#D3DBE6" stroke-width="2" fill="none"/>'
              '<path d="M247 262 L228 292" stroke="#D3DBE6" stroke-width="2" fill="none"/></g>')
    return left + right + pocket + lapels


def _steth(side_tube=True):
    tube = "#2A2F38"
    return ('<g id="stethoscope" fill="none" stroke-linecap="round">'
            '<path d="M150 254 C150 306 178 322 200 326" stroke="%s" stroke-width="6"/>'
            '<path d="M250 254 C250 306 222 322 200 326" stroke="%s" stroke-width="6"/>'
            '<path d="M200 326 C200 340 210 346 214 352" stroke="%s" stroke-width="6"/>'
            '<path d="M152 258 C153 296 176 316 198 322" stroke="#6C7684" stroke-width="1.6" opacity=".9"/>'
            '<path d="M248 258 C247 296 224 316 202 322" stroke="#6C7684" stroke-width="1.6" opacity=".9"/>'
            '<circle cx="200" cy="326" r="4.5" fill="#3B424D" stroke="none"/>'
            '</g>'
            '<g id="chestpiece"><circle cx="216" cy="363" r="14" fill="url(#metalG)" stroke="#59626F" stroke-width="2"/>'
            '<circle cx="216" cy="363" r="8.5" fill="#E9EDF2" stroke="#8B95A2" stroke-width="1.6"/>'
            '<circle cx="213" cy="360" r="3" fill="#fff" opacity=".9"/></g>') % (tube, tube, tube)


def _hand(x, y, kind="open", r=10):
    s = ['<circle cx="%.1f" cy="%.1f" r="%d" fill="url(#handG)" stroke="#BCA77A" stroke-width="1.8"/>' % (x, y, r)]
    if kind == "thumb":
        s.append('<ellipse cx="%.1f" cy="%.1f" rx="5.2" ry="9" fill="url(#handG)" stroke="#BCA77A" stroke-width="1.8"/>' % (x - 1, y - r - 4))
        s.append('<path d="M%.1f %.1f h9 M%.1f %.1f h8" stroke="#BCA77A" stroke-width="1.5" stroke-linecap="round"/>' % (x - 5, y + 1, x - 4, y + 5))
    elif kind == "point":
        s.append('<path d="M%.1f %.1f L%.1f %.1f" stroke="#BCA77A" stroke-width="9" stroke-linecap="round"/>' % (x + 5, y - 2, x + 22, y - 14))
        s.append('<path d="M%.1f %.1f L%.1f %.1f" stroke="url(#handG)" stroke-width="6.5" stroke-linecap="round"/>' % (x + 5, y - 2, x + 22, y - 14))
    return "".join(s)


def _thumbs_hand(x, y):
    """A big, unmistakable thumbs-up fist (thumb pointing straight up), drawn in Pilly's hand style."""
    return ('<rect x="%.1f" y="%.1f" width="12" height="28" rx="6" fill="url(#handG)" stroke="#BCA77A" stroke-width="1.8"/>'
            '<rect x="%.1f" y="%.1f" width="30" height="24" rx="9" fill="url(#handG)" stroke="#BCA77A" stroke-width="1.8"/>'
            '<path d="M%.1f %.1f h13 M%.1f %.1f h12 M%.1f %.1f h10" stroke="#BCA77A" stroke-width="1.5" stroke-linecap="round"/>'
            % (x - 13, y - 32, x - 15, y - 10, x - 1, y - 3, x - 1, y + 3, x - 1, y + 9))


def _arm(d, hand=None):
    """Sleeve = outlined white stroke; cuff ring is drawn near the hand."""
    return ('<path d="%s" fill="none" stroke="#A9B6C7" stroke-width="21" stroke-linecap="round" stroke-linejoin="round"/>'
            '<path d="%s" fill="none" stroke="#FFFFFF" stroke-width="17.5" stroke-linecap="round" stroke-linejoin="round"/>'
            % (d, d)) + (hand or "")


def _legs(jump=False):
    s = []
    if not jump:
        for x in (172, 228):
            s.append('<path d="M%d 402 L%d 440" stroke="#16335B" stroke-width="14" stroke-linecap="round"/>' % (x, x))
            s.append('<path d="M%d 402 L%d 440" stroke="#2F5A93" stroke-width="5" stroke-linecap="round" opacity=".6" transform="translate(-2 0)"/>' % (x, x))
            sx = -4 if x < 200 else 4
            s.append('<ellipse cx="%d" cy="446" rx="22" ry="11" fill="#1E3A5F" stroke="#0A1A33" stroke-width="2"/>' % (x + sx))
            s.append('<path d="M%d 452 h%d" stroke="#FBF3E0" stroke-width="3" stroke-linecap="round"/>' % (x + sx - 16, 32))
            s.append('<ellipse cx="%d" cy="441" rx="9" ry="3.6" fill="#fff" opacity=".35"/>' % (x + sx - 4))
    else:
        for x, dx in ((172, -1), (228, 1)):
            s.append('<path d="M%d 402 Q%d 424 %d 436" stroke="#16335B" stroke-width="14" stroke-linecap="round" fill="none"/>' % (x, x + dx * 10, x + dx * 22))
            s.append('<ellipse cx="%d" cy="440" rx="20" ry="10" fill="#1E3A5F" stroke="#0A1A33" stroke-width="2" transform="rotate(%d %d 440)"/>' % (x + dx * 28, dx * 18, x + dx * 28))
    return "".join(s)


def _sparkles(items):
    return "".join(_star(x, y, r, c, o) for x, y, r, c, o in items)


def _confetti(seed=7, n=34, area=(10, 20, 390, 330)):
    rnd = random.Random(seed)
    cols = [NAVY, GOLD, SAGE, "#F3D98B", "#6F93C4", "#E3B7A0"]
    out = []
    x0, y0, x1, y1 = area
    for _ in range(n):
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        if 100 < x < 300 and 90 < y < 330:  # keep the face clear
            x = x + (160 if x > 200 else -160)
        c = rnd.choice(cols)
        a = rnd.uniform(0, 180)
        if rnd.random() < .5:
            out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="1.5" fill="%s" transform="rotate(%.0f %.1f %.1f)"/>'
                       % (x, y, rnd.uniform(6, 11), rnd.uniform(3, 5), c, a, x, y))
        else:
            out.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s"/>' % (x, y, rnd.uniform(2.2, 3.6), c))
    return "".join(out)


def _bell(x, y, s=1.0):
    return ('<g transform="translate(%.1f %.1f) scale(%.2f)">'
            '<path d="M0 -13 C-9 -13 -11 -4 -11 4 L-14 11 L14 11 L11 4 C11 -4 9 -13 0 -13 Z" fill="%s" stroke="%s" stroke-width="1.6"/>'
            '<circle cx="0" cy="15" r="3.6" fill="%s" stroke="%s" stroke-width="1.2"/>'
            '<circle cx="0" cy="-15" r="2.2" fill="%s"/></g>' % (x, y, s, GOLD, GOLD_D, GOLD_D, GOLD_D, GOLD_D))


def _bulb(x, y):
    return ('<g transform="translate(%d %d)">'
            '<path d="M0 -20 C-13 -20 -17 -6 -9 3 C-6 7 -6 10 -6 13 L6 13 C6 10 6 7 9 3 C17 -6 13 -20 0 -20 Z" fill="#F7E3A1" stroke="%s" stroke-width="2"/>'
            '<rect x="-6" y="13" width="12" height="4" rx="2" fill="%s"/><rect x="-4.5" y="17.5" width="9" height="3.5" rx="1.7" fill="%s"/>'
            '<path d="M0 -26 v-6 M-18 -14 l-5 -3 M18 -14 l5 -3 M-23 0 h-6 M23 0 h6" stroke="%s" stroke-width="2.4" stroke-linecap="round"/></g>'
            % (x, y, GOLD_D, GOLD_D, GOLD_D, GOLD))


def build_svg(pose):
    if pose not in POSES:
        raise ValueError("unknown pose: %s" % pose)
    lift = 0
    mood = "smile"
    arms_back, arms_front, props, jump = "", "", "", False
    glasses = False

    arm_dl = _arm("M126 278 Q104 306 111 344", _hand(111, 351))
    arm_dr = _arm("M274 278 Q296 306 289 344", _hand(289, 351))

    if pose == "welcome":
        arms_front = arm_dl + _arm("M274 280 Q318 270 322 228", _hand(323, 216, r=11))
        props = ('<g stroke="%s" stroke-width="3.4" stroke-linecap="round" fill="none">'
                 '<path d="M345 205 q9 -4 12 -14"/><path d="M349 222 q11 -1 17 -9"/><path d="M296 190 q-3 -9 2 -17"/></g>'
                 % GOLD) + _sparkles([(66, 150, 11, GOLD, 1), (352, 120, 8, GOLD, .9), (90, 290, 6, GOLD, .7)])
    elif pose == "reminder":
        arms_front = arm_dl + _arm("M274 282 Q312 292 338 268", _hand(343, 262, "point", 10))
        props = ('<g><rect x="316" y="150" width="98" height="64" rx="14" fill="#FFFFFF" stroke="%s" stroke-width="2.6"/>'
                 '<rect x="316" y="150" width="98" height="64" rx="14" fill="none" stroke="%s" stroke-width="1" opacity=".5" transform="translate(2 3)"/>'
                 % (NAVY, GOLD)) + _bell(344, 182, 1.0) + (
                 '<rect x="364" y="170" width="38" height="6" rx="3" fill="%s"/><rect x="364" y="184" width="26" height="6" rx="3" fill="#C9D3E0"/></g>' % SAGE
                 ) + _sparkles([(404, 142, 9, GOLD, 1), (62, 160, 8, GOLD, .85)])
    elif pose == "completed":
        mood = "happy"
        arms_front = arm_dl + _arm("M274 280 Q312 290 307 256", _hand(307, 244, "thumb", 11))
        props = _sparkles([(338, 196, 10, GOLD, 1), (70, 160, 9, GOLD, .9), (356, 256, 6, GOLD, .8)])
        props += '<path d="M330 284 l7 8 l14 -17" stroke="%s" stroke-width="7" fill="none" stroke-linecap="round" stroke-linejoin="round"/>' % SAGE
    elif pose == "thumbsup":
        mood = "happy"
        arms_front = arm_dl + _arm("M274 280 Q324 274 322 236", _thumbs_hand(322, 222))
        props = (_sparkles([(358, 170, 11, GOLD, 1), (64, 158, 9, GOLD, .9), (366, 262, 7, GOLD, .8), (58, 262, 6, GOLD, .7)])
                 + _confetti(5, 14, (20, 40, 380, 320)))
    elif pose == "progress":
        mood = "happy"
        arms_front = _arm("M126 278 Q86 266 82 222", _hand(81, 210, r=11)) + _arm("M274 278 Q314 266 318 222", _hand(319, 210, r=11))
        props = _confetti(11, 22, (20, 40, 380, 320)) + _sparkles([(64, 120, 11, GOLD, 1), (338, 110, 11, GOLD, 1), (200, 52, 9, GOLD, .9)])
    elif pose == "achievement":
        mood = "wow"
        lift = -38
        jump = True
        arms_front = _arm("M126 278 Q84 258 76 212", _hand(75, 200, r=11)) + _arm("M274 278 Q316 258 324 212", _hand(325, 200, r=11))
        props = _confetti(3, 46, (6, 14, 394, 400)) + _sparkles([(58, 118, 13, GOLD, 1), (346, 98, 13, GOLD, 1), (200, 34, 10, GOLD, 1), (92, 372, 8, GOLD, .9), (322, 360, 9, GOLD, .9)])
    elif pose == "tips":
        mood = "think"
        glasses = True
        arms_front = arm_dl + _arm("M274 282 Q304 286 268 250", _hand(258, 241, r=9.5))
        props = _bulb(330, 128) + _sparkles([(74, 150, 8, GOLD, .8)])

    shadow_w = 70 if not jump else 46
    shadow_o = 1 if not jump else .55
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">' % (W, H, W, H), _defs(),
           '<g transform="translate(40 0)">',
           '<ellipse cx="200" cy="458" rx="%d" ry="12" fill="url(#shadowG)" opacity="%s"/>' % (shadow_w, shadow_o),
           '<g transform="translate(0 %d)">' % lift,
           _legs(jump), _body(), _face(mood), _glasses() if glasses else "",
           _coat(), _steth(), arms_front,
           "</g>", props, "</g></svg>"]
    return "\n".join(svg)


def _png(svg_path, png_path, width=720):
    exe = shutil.which("rsvg-convert")
    if exe:
        subprocess.run([exe, "-w", str(width), "-o", png_path, svg_path], check=True)
        return
    import cairosvg  # optional fallback
    cairosvg.svg2png(url=svg_path, write_to=png_path, output_width=width)


def _icon(out_dir):
    """64px browser-tab icon: Pilly's navy head, cropped from the welcome pose."""
    from PIL import Image
    im = Image.open(os.path.join(out_dir, "pilly_welcome.png")).convert("RGBA")
    w, h = im.size
    box = (int(w * 0.30), int(h * 0.12), int(w * 0.70), int(h * 0.12 + w * 0.40))
    ico = im.crop(box).resize((96, 96), Image.LANCZOS)
    path = os.path.join(out_dir, "pilly_icon.png")
    ico.save(path)
    return path


def generate(out_dir=None):
    out_dir = out_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "pilly")
    os.makedirs(out_dir, exist_ok=True)
    made = []
    for pose in POSES:
        sp = os.path.join(out_dir, "pilly_%s.svg" % pose)
        with open(sp, "w", encoding="utf-8") as fh:
            fh.write(build_svg(pose))
        pp = os.path.join(out_dir, "pilly_%s.png" % pose)
        _png(sp, pp)
        made.append(pp)
    made.append(_icon(out_dir))
    return made


if __name__ == "__main__":
    for p in generate():
        print("wrote", p)
'''),
('db', r'''"""SQLite persistence. One short-lived connection per call; safe with Streamlit's threads."""
import contextlib
import datetime as dt
import os
import sqlite3

from . import config as C

SCHEMA = """
CREATE TABLE IF NOT EXISTS profile(
    id INTEGER PRIMARY KEY CHECK (id = 1), name TEXT NOT NULL DEFAULT '', age INTEGER,
    tz TEXT NOT NULL DEFAULT 'Asia/Kolkata', onboarded INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS medicines(
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, time TEXT NOT NULL,
    days TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '', created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS dose_log(
    med_id INTEGER NOT NULL, date TEXT NOT NULL, taken_at TEXT NOT NULL,
    PRIMARY KEY (med_id, date), FOREIGN KEY (med_id) REFERENCES medicines(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS reminder_state(
    med_id INTEGER NOT NULL, date TEXT NOT NULL, status TEXT NOT NULL,
    snooze_until TEXT, fired_at TEXT, PRIMARY KEY (med_id, date),
    FOREIGN KEY (med_id) REFERENCES medicines(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS reminder_events(
    id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, med_id INTEGER, med_name TEXT NOT NULL,
    scheduled TEXT NOT NULL, event TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS achievements(
    key TEXT PRIMARY KEY, unlocked_at TEXT NOT NULL, celebrated INTEGER NOT NULL DEFAULT 0);
"""


@contextlib.contextmanager
def conn():
    os.makedirs(os.path.dirname(C.DB_PATH), exist_ok=True)
    c = sqlite3.connect(C.DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()


def init_db():
    with conn() as c:
        c.executescript(SCHEMA)
        c.execute("INSERT OR IGNORE INTO profile(id) VALUES (1)")
        for k, v in C.DEFAULT_SETTINGS.items():
            c.execute("INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)", (k, v))


# ---------------------------------------------------------------- profile
def get_profile():
    with conn() as c:
        r = c.execute("SELECT * FROM profile WHERE id = 1").fetchone()
    return {"name": r["name"], "age": r["age"], "tz": r["tz"], "onboarded": bool(r["onboarded"])}


def save_profile(name=None, age="keep", tz=None, onboarded=None):
    sets, vals = [], []
    if name is not None:
        sets.append("name = ?"); vals.append(name.strip())
    if age != "keep":
        sets.append("age = ?"); vals.append(age)
    if tz is not None:
        sets.append("tz = ?"); vals.append(tz)
    if onboarded is not None:
        sets.append("onboarded = ?"); vals.append(1 if onboarded else 0)
    if sets:
        with conn() as c:
            c.execute("UPDATE profile SET %s WHERE id = 1" % ", ".join(sets), vals)


# --------------------------------------------------------------- settings
def get_settings():
    with conn() as c:
        rows = c.execute("SELECT key, value FROM settings").fetchall()
    out = dict(C.DEFAULT_SETTINGS)
    out.update({r["key"]: r["value"] for r in rows})
    return out


def set_setting(key, value):
    if key not in C.DEFAULT_SETTINGS:
        raise KeyError(key)
    with conn() as c:
        c.execute("INSERT INTO settings(key, value) VALUES (?, ?) "
                  "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, str(value)))


# --------------------------------------------------------------- medicines
def _med(r):
    return {"id": r["id"], "name": r["name"], "time": r["time"], "notes": r["notes"], "created": r["created"],
            "days": sorted(int(x) for x in r["days"].split(",") if x != "")}


def list_meds():
    with conn() as c:
        rows = c.execute("SELECT * FROM medicines ORDER BY time, name COLLATE NOCASE").fetchall()
    return [_med(r) for r in rows]


def get_med(med_id):
    with conn() as c:
        r = c.execute("SELECT * FROM medicines WHERE id = ?", (med_id,)).fetchone()
    return _med(r) if r else None


def validate_med(name, time_s, days, notes=""):
    """Return a clean (name, time, days, notes) or raise ValueError with a friendly message."""
    name = (name or "").strip()
    if not name:
        raise ValueError("Please enter the medicine name.")
    if len(name) > 60:
        raise ValueError("The medicine name is too long (60 characters max).")
    try:
        h, m = time_s.split(":")
        assert 0 <= int(h) <= 23 and 0 <= int(m) <= 59
    except Exception:
        raise ValueError("Please choose a valid time.")
    days = sorted({int(d) for d in days})
    if not days or any(d < 0 or d > 6 for d in days):
        raise ValueError("Please pick at least one day.")
    notes = (notes or "").strip()
    if len(notes) > 200:
        raise ValueError("Notes are too long (200 characters max).")
    return name, "%02d:%02d" % (int(h), int(m)), days, notes


def add_med(name, time_s, days, notes="", today=None):
    name, time_s, days, notes = validate_med(name, time_s, days, notes)
    with conn() as c:
        dup = c.execute("SELECT 1 FROM medicines WHERE lower(name) = lower(?) AND time = ? AND days = ?",
                        (name, time_s, ",".join(map(str, days)))).fetchone()
        if dup:
            raise ValueError("That medicine is already scheduled at this time and on these days.")
        cur = c.execute("INSERT INTO medicines(name, time, days, notes, created) VALUES (?, ?, ?, ?, ?)",
                        (name, time_s, ",".join(map(str, days)), notes, (today or dt.date.today()).isoformat()))
        return cur.lastrowid


def update_med(med_id, name, time_s, days, notes=""):
    name, time_s, days, notes = validate_med(name, time_s, days, notes)
    with conn() as c:
        if not c.execute("SELECT 1 FROM medicines WHERE id = ?", (med_id,)).fetchone():
            raise ValueError("That medicine no longer exists.")
        c.execute("UPDATE medicines SET name = ?, time = ?, days = ?, notes = ? WHERE id = ?",
                  (name, time_s, ",".join(map(str, days)), notes, med_id))
        # a changed time/days means today's reminder should be re-evaluated
        c.execute("DELETE FROM reminder_state WHERE med_id = ?", (med_id,))


def delete_med(med_id):
    with conn() as c:
        c.execute("DELETE FROM medicines WHERE id = ?", (med_id,))  # logs/reminder state cascade


# ------------------------------------------------------------------- doses
def get_log(start=None, end=None):
    """{(date_iso, med_id): 'HH:MM'} for the inclusive range."""
    q, args = "SELECT med_id, date, taken_at FROM dose_log", []
    if start and end:
        q += " WHERE date BETWEEN ? AND ?"
        args = [start.isoformat(), end.isoformat()]
    with conn() as c:
        rows = c.execute(q, args).fetchall()
    return {(r["date"], r["med_id"]): r["taken_at"] for r in rows}


def mark_taken(med_id, day, hhmm):
    with conn() as c:
        c.execute("INSERT INTO dose_log(med_id, date, taken_at) VALUES (?, ?, ?) "
                  "ON CONFLICT(med_id, date) DO UPDATE SET taken_at = excluded.taken_at",
                  (med_id, day.isoformat(), hhmm))
        c.execute("INSERT INTO reminder_state(med_id, date, status) VALUES (?, ?, 'taken') "
                  "ON CONFLICT(med_id, date) DO UPDATE SET status = 'taken', snooze_until = NULL",
                  (med_id, day.isoformat()))


def unmark_taken(med_id, day):
    with conn() as c:
        c.execute("DELETE FROM dose_log WHERE med_id = ? AND date = ?", (med_id, day.isoformat()))
        c.execute("DELETE FROM reminder_state WHERE med_id = ? AND date = ? AND status = 'taken'",
                  (med_id, day.isoformat()))


# --------------------------------------------------------------- reminders
def get_reminder_state(day):
    with conn() as c:
        rows = c.execute("SELECT * FROM reminder_state WHERE date = ?", (day.isoformat(),)).fetchall()
    return {r["med_id"]: {"status": r["status"], "snooze_until": r["snooze_until"], "fired_at": r["fired_at"]}
            for r in rows}


def mark_fired(med_id, day, now):
    """Atomically claim a reminder. Returns True only the first time (prevents duplicate pop-ups)."""
    with conn() as c:
        cur = c.execute("INSERT OR IGNORE INTO reminder_state(med_id, date, status, fired_at) VALUES (?, ?, 'fired', ?)",
                        (med_id, day.isoformat(), now.isoformat(timespec="seconds")))
        return cur.rowcount == 1


def refire_snoozed(med_id, day, now):
    """Claim a snoozed reminder whose time has come. True only once."""
    with conn() as c:
        cur = c.execute("UPDATE reminder_state SET status = 'fired', fired_at = ? "
                        "WHERE med_id = ? AND date = ? AND status = 'snoozed' AND snooze_until <= ?",
                        (now.isoformat(timespec="seconds"), med_id, day.isoformat(), now.isoformat(timespec="seconds")))
        return cur.rowcount == 1


def snooze(med_id, day, until):
    with conn() as c:
        c.execute("INSERT INTO reminder_state(med_id, date, status, snooze_until) VALUES (?, ?, 'snoozed', ?) "
                  "ON CONFLICT(med_id, date) DO UPDATE SET status = 'snoozed', snooze_until = excluded.snooze_until",
                  (med_id, day.isoformat(), until.isoformat(timespec="seconds")))


def add_event(now, med, scheduled, event, detail=""):
    with conn() as c:
        c.execute("INSERT INTO reminder_events(at, med_id, med_name, scheduled, event, detail) VALUES (?, ?, ?, ?, ?, ?)",
                  (now.isoformat(timespec="seconds"), med["id"], med["name"], scheduled, event, detail))


def list_events(limit=200):
    with conn() as c:
        rows = c.execute("SELECT at, med_name, scheduled, event, detail FROM reminder_events "
                         "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


# ------------------------------------------------------------ achievements
def get_achievements():
    with conn() as c:
        rows = c.execute("SELECT key, unlocked_at, celebrated FROM achievements").fetchall()
    return {r["key"]: {"at": r["unlocked_at"], "celebrated": bool(r["celebrated"])} for r in rows}


def unlock(key, now):
    """True only when newly unlocked."""
    with conn() as c:
        cur = c.execute("INSERT OR IGNORE INTO achievements(key, unlocked_at, celebrated) VALUES (?, ?, 0)",
                        (key, now.isoformat(timespec="seconds")))
        return cur.rowcount == 1


def mark_celebrated(key):
    with conn() as c:
        c.execute("UPDATE achievements SET celebrated = 1 WHERE key = ?", (key,))


# ---------------------------------------------------------- data management
def clear_day_log(day):
    with conn() as c:
        c.execute("DELETE FROM dose_log WHERE date = ?", (day.isoformat(),))
        c.execute("DELETE FROM reminder_state WHERE date = ?", (day.isoformat(),))


def clear_history(keep_today=None):
    with conn() as c:
        c.execute("DELETE FROM reminder_events")


def reset_everything():
    with conn() as c:
        for t in ("dose_log", "reminder_state", "reminder_events", "achievements", "medicines", "settings"):
            c.execute("DELETE FROM %s" % t)
        c.execute("DELETE FROM sqlite_sequence")
        c.execute("UPDATE profile SET name = '', age = NULL, tz = 'Asia/Kolkata', onboarded = 0 WHERE id = 1")
        for k, v in C.DEFAULT_SETTINGS.items():
            c.execute("INSERT INTO settings(key, value) VALUES (?, ?)", (k, v))


def export_all():
    """Everything as a JSON-able dict (for the backup download)."""
    with conn() as c:
        data = {t: [dict(r) for r in c.execute("SELECT * FROM %s" % t).fetchall()]
                for t in ("profile", "settings", "medicines", "dose_log", "reminder_events", "achievements")}
    return data
'''),
('logic', r'''"""Pure scheduling / statistics logic (no Streamlit, no database) so it can be unit-tested."""
import datetime as dt

import pandas as pd

from .config import DAYS, SNOOZE_MAX, SNOOZE_MIN


# ----------------------------------------------------------------- formatting
def parse_hm(s):
    h, m = s.split(":")
    return int(h), int(m)


def to_time(s):
    h, m = parse_hm(s)
    return dt.time(h, m)


def fmt_time(s, h24=False):
    h, m = parse_hm(s)
    if h24:
        return "%02d:%02d" % (h, m)
    return "%d:%02d %s" % (h % 12 or 12, m, "AM" if h < 12 else "PM")


def fmt_days(days):
    days = sorted(days)
    if len(days) == 7:
        return "Every day"
    if days == [0, 1, 2, 3, 4]:
        return "Weekdays"
    if days == [5, 6]:
        return "Weekends"
    return ", ".join(DAYS[i] for i in days)


def greeting(now):
    return "Good morning" if now.hour < 12 else "Good afternoon" if now.hour < 17 else "Good evening"


# ------------------------------------------------------------------- doses
def doses_for_day(meds, day):
    iso = day.isoformat()
    return sorted((m for m in meds if day.weekday() in m["days"] and iso >= m["created"]),
                  key=lambda m: (m["time"], m["name"].lower()))


def due_at(m, day):
    return dt.datetime.combine(day, to_time(m["time"]))


def clamp_snooze(v, default=10):
    """Snooze length in whole minutes, kept inside the allowed range."""
    try:
        v = int(v)
    except (TypeError, ValueError):
        v = default
    return max(SNOOZE_MIN, min(SNOOZE_MAX, v))


def snoozed_until(st, now):
    """When a still-waiting snoozed reminder will fire (a datetime), else None. `st` is one reminder_state entry."""
    if st and st.get("status") == "snoozed" and st.get("snooze_until"):
        when = _parse_iso(st["snooze_until"])
        if when > now:
            return when
    return None


def status_of(m, day, now, log, window, state=None):
    """'taken' | 'upcoming' (not yet due, or due and still inside the window) | 'missed'.
    `state` (today's reminder_state) lets a snoozed dose stay 'upcoming' until its snooze has run out
    plus one window, instead of turning 'missed' while the user is waiting for the reminder."""
    if (day.isoformat(), m["id"]) in log:
        return "taken"
    due = due_at(m, day)
    if now < due:
        return "upcoming"
    if day == now.date():
        last = due
        st = (state or {}).get(m["id"])
        if st and st.get("snooze_until"):
            last = max(last, _parse_iso(st["snooze_until"]))
        if now < last + dt.timedelta(minutes=window):
            return "upcoming"
    return "missed"


def is_due_now(m, day, now, log, window, state=None):
    if snoozed_until((state or {}).get(m["id"]), now):
        return False                      # snoozed: the user asked to be reminded later
    return status_of(m, day, now, log, window, state) == "upcoming" and due_at(m, day) <= now


def day_stats(meds, day, now, log, window, state=None):
    out = {"taken": 0, "upcoming": 0, "missed": 0}
    for m in doses_for_day(meds, day):
        out[status_of(m, day, now, log, window, state)] += 1
    out["total"] = out["taken"] + out["upcoming"] + out["missed"]
    out["due"] = out["taken"] + out["missed"]
    out["pct"] = (100.0 * out["taken"] / out["due"]) if out["due"] else None
    return out


def week_days(today):
    mon = today - dt.timedelta(days=today.weekday())
    return [mon + dt.timedelta(days=i) for i in range(7)]


def week_frame(meds, today, now, log, window, days=None, state=None):
    """Seven-day DataFrame (pandas) used by the chart, the screen and the reports."""
    rows = []
    for d in (days or week_days(today)):
        s = day_stats(meds, d, now, log, window, state)
        rows.append({"date": d, "day": DAYS[d.weekday()], "scheduled": s["total"], "taken": s["taken"],
                     "missed": s["missed"], "upcoming": s["upcoming"], "due": s["due"],
                     "adherence": s["pct"]})
    return pd.DataFrame(rows)


def week_summary(df):
    taken, missed = int(df["taken"].sum()), int(df["missed"].sum())
    due = taken + missed
    return {"scheduled": int(df["scheduled"].sum()), "taken": taken, "missed": missed,
            "upcoming": int(df["upcoming"].sum()), "due": due,
            "pct": (100.0 * taken / due) if due else None}


def dose_history(meds, today, now, log, window, n_days, state=None):
    """[(date, [dose, ...])] for the last n_days, newest first; only days that had doses."""
    out = []
    for off in range(n_days):
        day = today - dt.timedelta(days=off)
        rows = [{"med": m["name"], "time": m["time"], "notes": m["notes"],
                 "status": status_of(m, day, now, log, window, state),
                 "taken_at": log.get((day.isoformat(), m["id"]), "")} for m in doses_for_day(meds, day)]
        if rows:
            out.append((day, rows))
    return out


def earliest_day(meds):
    return min((dt.date.fromisoformat(m["created"]) for m in meds), default=None)


def streak(meds, today, now, log, window, state=None):
    """Consecutive days (ending today) with at least one dose taken and none missed."""
    start = earliest_day(meds)
    if not start:
        return 0
    n, day = 0, today
    while day >= start:
        s = day_stats(meds, day, now, log, window, state)
        if s["missed"] > 0:
            break
        if s["taken"] > 0:
            n += 1
        day -= dt.timedelta(days=1)
    return n


# --------------------------------------------------------------- reminders
def _parse_iso(s):
    return dt.datetime.fromisoformat(s)


def pending_reminders(meds, day, now, log, state, window):
    """Doses whose reminder should pop up right now: (med, 'new'|'snoozed'), earliest first."""
    out = []
    for m in doses_for_day(meds, day):
        if (day.isoformat(), m["id"]) in log:
            continue
        st = state.get(m["id"])
        due = due_at(m, day)
        if st is None:
            if due <= now < due + dt.timedelta(minutes=window):
                out.append((m, "new"))
        elif st["status"] == "snoozed" and st.get("snooze_until") and _parse_iso(st["snooze_until"]) <= now:
            out.append((m, "snoozed"))
    return sorted(out, key=lambda t: due_at(t[0], day))


def next_reminder(meds, now, log, state, window, horizon=7):
    """Next time MedTimer will remind: a snoozed reminder or the next scheduled dose."""
    best = None
    for off in range(horizon + 1):
        day = now.date() + dt.timedelta(days=off)
        for m in doses_for_day(meds, day):
            if (day.isoformat(), m["id"]) in log:
                continue
            when, kind = due_at(m, day), "scheduled"
            st = state.get(m["id"]) if off == 0 else None
            if st and st["status"] == "snoozed" and st.get("snooze_until"):
                when, kind = _parse_iso(st["snooze_until"]), "snoozed"
            elif st:
                continue  # already reminded today
            if when > now and (best is None or when < best["when"]):
                best = {"med": m, "when": when, "kind": kind}
        if best and off >= 0 and best["when"].date() == day:
            break
    return best


def fmt_when(when, now, h24=False):
    t = fmt_time(when.strftime("%H:%M"), h24)
    d = (when.date() - now.date()).days
    if d == 0:
        return "today at " + t
    if d == 1:
        return "tomorrow at " + t
    return "%s at %s" % (DAYS[when.weekday()], t)


# ------------------------------------------------------------ achievements
ACHIEVEMENTS = {
    "first_day": ("First Day Completed", "Take every scheduled dose on one full day.",
                  "You did it, {n}! Your first day is complete!"),
    "consistency": ("Consistency Champion", "Three days in a row with no missed doses.",
                    "You did it, {n}! You're a Consistency Champion!"),
    "weekly_star": ("Weekly Progress Star", "Reach 90% or more in a week (at least 3 doses).",
                    "Brilliant, {n}! You're a Weekly Progress Star!"),
    "routine_builder": ("Routine Builder", "Log your doses on five different days.",
                        "Lovely, {n}! You're a Routine Builder!"),
}


def achievement_message(key, name):
    return ACHIEVEMENTS[key][2].format(n=name or "friend")


def evaluate_achievements(meds, log, today, now, window, state=None):
    earned = set()
    start = earliest_day(meds)
    if not start:
        return earned
    if len({d for (d, _m) in log}) >= 5:
        earned.add("routine_builder")
    day = start
    while day <= today:
        s = day_stats(meds, day, now, log, window, state)
        if s["total"] and s["taken"] == s["total"]:
            earned.add("first_day")
            break
        day += dt.timedelta(days=1)
    if streak(meds, today, now, log, window, state) >= 3:
        earned.add("consistency")
    mon = start - dt.timedelta(days=start.weekday())
    while mon <= today:
        s = week_summary(week_frame(meds, today, now, log, window, [mon + dt.timedelta(days=i) for i in range(7)], state))
        if s["due"] >= 3 and s["pct"] is not None and s["pct"] >= 90:
            earned.add("weekly_star")
            break
        mon += dt.timedelta(days=7)
    return earned


# ------------------------------------------------------------ Pilly's words
def pilly_message(stats, name):
    n = name or "friend"
    if stats["total"] == 0:
        return "Nothing scheduled today, %s. Enjoy a calm day!" % n
    if stats["taken"] == stats["total"]:
        return "All done for today, %s. Wonderful consistency!" % n
    if stats["missed"] and not stats["upcoming"]:
        return "Today's log is waiting for you, %s. Tick off anything you've already taken." % n
    if stats["upcoming"]:
        return "You're doing well, %s. Your next dose is coming up." % n
    return "Keep going, %s. Pilly is cheering for you!" % n


TAKEN_MESSAGES = [
    "Lovely, {n}! That's one more ticked off.",
    "Well done, {n}! Every check-in builds your routine.",
    "Wonderful, {n}. Pilly is proud of you!",
    "Nicely done, {n}. Keep it up!",
]
'''),
('reports', r'''"""Report building with pandas: daily, weekly, schedule and reminder history (CSV + readable text)."""
import io

import pandas as pd

from . import logic as L
from .config import DAYS


def daily_df(meds, day, now, log, window, h24=False, state=None):
    rows = []
    for m in L.doses_for_day(meds, day):
        st = L.status_of(m, day, now, log, window, state)
        at = log.get((day.isoformat(), m["id"]), "")
        rows.append({"Time": L.fmt_time(m["time"], h24), "Medicine": m["name"], "Status": st.capitalize(),
                     "Taken at": L.fmt_time(at, h24) if at else "", "Notes": m["notes"]})
    return pd.DataFrame(rows, columns=["Time", "Medicine", "Status", "Taken at", "Notes"])


def weekly_df(meds, today, now, log, window, state=None):
    df = L.week_frame(meds, today, now, log, window, state=state)
    out = pd.DataFrame({"Date": df["date"].map(lambda d: d.isoformat()), "Day": df["day"],
                        "Scheduled": df["scheduled"], "Taken": df["taken"], "Missed": df["missed"],
                        "Still to come": df["upcoming"],
                        "Adherence %": df["adherence"].map(lambda v: "" if pd.isna(v) else round(v))})
    return out, L.week_summary(df)


def schedule_df(meds, h24=False):
    return pd.DataFrame([{"Medicine": m["name"], "Time": L.fmt_time(m["time"], h24), "Days": L.fmt_days(m["days"]),
                          "Notes": m["notes"]} for m in meds], columns=["Medicine", "Time", "Days", "Notes"])


def log_df(history, h24=False):
    """Flat table of L.dose_history() output (one row per dose) for the History download."""
    rows = [{"Date": d.isoformat(), "Day": DAYS[d.weekday()], "Time": L.fmt_time(r["time"], h24), "Medicine": r["med"],
             "Status": r["status"].capitalize(), "Taken at": L.fmt_time(r["taken_at"], h24) if r["taken_at"] else ""}
            for d, doses in history for r in doses]
    return pd.DataFrame(rows, columns=["Date", "Day", "Time", "Medicine", "Status", "Taken at"])


def history_df(events):
    return pd.DataFrame(events, columns=["at", "med_name", "scheduled", "event", "detail"]).rename(
        columns={"at": "When", "med_name": "Medicine", "scheduled": "Scheduled", "event": "Event", "detail": "Details"})


def to_csv(df):
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8-sig")  # BOM so Excel opens it correctly


def to_text(title, profile, now, df, footer=None):
    lines = ["MedTimer - %s" % title, "=" * 56, "Name      : %s" % (profile.get("name") or "-"),
             "Generated : %s" % now.strftime("%a %d %b %Y, %I:%M %p"), ""]
    lines.append(df.to_string(index=False) if len(df) else "(nothing to show)")
    if footer:
        lines += [""] + footer
    lines += ["", "-" * 56, "MedTimer tracks and reminds. It does not give medical advice."]
    return ("\n".join(lines) + "\n").encode("utf-8")
'''),
('audio', r'''"""Reminder sounds, synthesised in pure Python (no audio files needed)."""
import io
import math
import struct
import wave

RATE = 22050

# (frequency Hz, start s, length s)
SOUNDS = {
    "chime": [(1046.5, 0.00, 0.9), (1318.5, 0.18, 0.9), (1568.0, 0.36, 1.2)],
    "bell": [(880.0, 0.00, 1.6), (1760.0, 0.00, 0.8), (2217.0, 0.00, 0.4)],
    "ding": [(1396.9, 0.00, 0.55), (1396.9, 0.45, 0.8)],
    # played when a dose is logged: a quick, bright rising "success" arpeggio, clearly different from the reminder sounds
    "taken": [(523.3, 0.00, 0.35), (659.3, 0.11, 0.35), (784.0, 0.22, 0.35), (1046.5, 0.33, 0.8)],
}


def make_wav(name="chime", volume=70):
    notes = SOUNDS.get(name, SOUNDS["chime"])
    vol = max(0, min(100, int(volume))) / 100.0
    total = max(s + l for _f, s, l in notes) + 0.1
    n = int(RATE * total)
    buf = [0.0] * n
    for freq, start, length in notes:
        i0, cnt = int(start * RATE), int(length * RATE)
        for i in range(cnt):
            if i0 + i >= n:
                break
            t = i / RATE
            env = min(1.0, i / (0.01 * RATE)) * math.exp(-3.4 * t / length)
            v = math.sin(2 * math.pi * freq * t) + 0.25 * math.sin(2 * math.pi * freq * 2 * t)
            buf[i0 + i] += 0.35 * env * v
    peak = max(1.0, max(abs(x) for x in buf))
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(32767 * vol * x / peak)) for x in buf))
    return out.getvalue()


_cache = {}


def make_wav_cached(name="chime", volume=70):
    """Synthesise each (sound, volume) once per process."""
    key = (name, int(volume))
    if key not in _cache:
        _cache[key] = make_wav(name, volume)
    return _cache[key]
'''),
('turtle_badge', r'''"""
Turtle-graphics achievement badge.

The drawing code (`draw_badge`) is written ONLY with the standard Python `turtle` API
(penup, goto, forward, left, circle, begin_fill ...), so it runs unchanged on:

  * the real `turtle` module:      python -m medtimer.turtle_badge --live
  * PILTurtle (below), a tiny headless implementation of the same API that renders to a PNG.

Why PILTurtle?  The real turtle needs Tkinter and a screen window, and Tkinter must run on a
process's main thread - something Streamlit's script threads cannot guarantee (on macOS it
aborts the whole app). PILTurtle replays the same turtle commands into an image instead, so
the badge can be generated safely inside Streamlit, on servers and in tests.
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

from . import config as C

SS = 3  # supersampling factor for smooth edges


class PILTurtle:
    """Minimal headless drop-in for turtle.Turtle (only what draw_badge needs)."""

    def __init__(self, size=(600, 600), bg="#FBF7EC"):
        self.w, self.h = size
        self.img = Image.new("RGB", (self.w * SS, self.h * SS), bg)
        self.d = ImageDraw.Draw(self.img)
        self._x = self._y = 0.0
        self._heading = 0.0
        self._down = True
        self._pen, self._fill = "black", "black"
        self._size = 1
        self._poly = None

    # -- state ---------------------------------------------------------
    def speed(self, *_a): pass
    def hideturtle(self): pass
    def tracer(self, *_a): pass
    def pensize(self, w): self._size = w
    def width(self, w): self._size = w
    def penup(self): self._down = False
    def pendown(self): self._down = True
    def pencolor(self, c): self._pen = c
    def fillcolor(self, c): self._fill = c

    def color(self, pen, fill=None):
        self._pen = pen
        self._fill = fill if fill is not None else pen

    def pos(self): return (self._x, self._y)
    def xcor(self): return self._x
    def ycor(self): return self._y
    def heading(self): return self._heading
    def setheading(self, a): self._heading = a % 360
    def left(self, a): self._heading = (self._heading + a) % 360
    def right(self, a): self._heading = (self._heading - a) % 360
    lt, rt, setpos, setposition = left, right, None, None

    # -- geometry ------------------------------------------------------
    def _px(self, x, y):
        return ((x + self.w / 2) * SS, (self.h / 2 - y) * SS)

    def _move_to(self, x, y):
        if self._down:
            self.d.line([self._px(self._x, self._y), self._px(x, y)], fill=self._pen,
                        width=max(1, int(self._size * SS)))
            r = self._size * SS / 2
            px, py = self._px(x, y)
            self.d.ellipse([px - r, py - r, px + r, py + r], fill=self._pen)
        self._x, self._y = x, y
        if self._poly is not None:
            self._poly.append((x, y))

    def goto(self, x, y=None):
        if y is None:
            x, y = x
        self._move_to(x, y)
    setpos = setposition = goto

    def setx(self, x): self.goto(x, self._y)
    def sety(self, y): self.goto(self._x, y)

    def forward(self, dist):
        a = math.radians(self._heading)
        self._move_to(self._x + dist * math.cos(a), self._y + dist * math.sin(a))
    fd = forward

    def backward(self, dist): self.forward(-dist)
    bk = back = backward

    def circle(self, radius, extent=360, steps=None):
        """Same semantics as turtle.circle: centre is `radius` to the turtle's left."""
        steps = steps or max(8, int(abs(radius) * min(abs(extent), 360) / 360 * 0.9) + 8)
        step_ang = extent / steps
        chord = 2 * radius * math.sin(math.radians(abs(step_ang) / 2)) * (1 if radius > 0 else -1)
        self.left(step_ang / 2)
        for _ in range(steps):
            self.forward(chord if extent >= 0 else -chord)
            self.left(step_ang)
        self.right(step_ang / 2)

    def dot(self, size=None, color=None):
        size = size or max(self._size + 4, 2 * self._size)
        px, py = self._px(self._x, self._y)
        r = size * SS / 2
        self.d.ellipse([px - r, py - r, px + r, py + r], fill=color or self._pen)

    def begin_fill(self): self._poly = [(self._x, self._y)]

    def end_fill(self):
        if self._poly and len(self._poly) > 2:
            self.d.polygon([self._px(x, y) for x, y in self._poly], fill=self._fill)
        self._poly = None

    def write(self, text, move=False, align="left", font=("Georgia", 12, "normal")):
        size = int(font[1] * SS * 1.35)
        bold = len(font) > 2 and "bold" in font[2]
        names = (["DejaVuSerif-Bold.ttf", "LiberationSerif-Bold.ttf", "georgiab.ttf", "Georgia Bold.ttf"] if bold else
                 ["DejaVuSerif.ttf", "LiberationSerif-Regular.ttf", "georgia.ttf", "Georgia.ttf"])
        f = None
        for n in names:
            try:
                f = ImageFont.truetype(n, size)
                break
            except Exception:
                continue
        f = f or ImageFont.load_default()
        px, py = self._px(self._x, self._y)
        anchor = {"left": "ls", "center": "ms", "right": "rs"}[align]
        self.d.text((px, py + size * 0.0), text, fill=self._pen, font=f, anchor=anchor)

    def image(self):
        return self.img.resize((self.w, self.h), Image.LANCZOS)


# ---------------------------------------------------------------- the drawing
def _poly(t, pts, pen, fill, width=2):
    """Filled polygon using only goto/begin_fill (standard turtle commands)."""
    t.penup(); t.goto(*pts[0]); t.pendown(); t.pensize(width); t.color(pen, fill); t.begin_fill()
    for x, y in pts[1:] + [pts[0]]:
        t.goto(x, y)
    t.end_fill(); t.penup()


def _star(t, cx, cy, r, fill, pen=None):
    pts = []
    for i in range(10):
        rad = r if i % 2 == 0 else r * 0.42
        a = math.radians(90 + i * 36)
        pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    _poly(t, pts, pen or fill, fill, 2)


def _disc(t, cx, cy, r, pen, fill, width=2):
    t.penup(); t.goto(cx, cy - r); t.setheading(0); t.pendown()
    t.pensize(width); t.color(pen, fill); t.begin_fill(); t.circle(r); t.end_fill(); t.penup()


def _leaf(t, x, y, heading, size, color):
    t.penup(); t.goto(x, y); t.setheading(heading); t.pendown()
    t.pensize(1); t.color("#5E8059", color); t.begin_fill()
    t.circle(size, 60); t.left(120); t.circle(size, 60)
    t.end_fill(); t.penup()


def draw_badge(t, title="MedTimer", subtitle="Achievement", count=0, total=4, name=""):
    """Draw the medallion. Only standard turtle commands are used here."""
    NAVY, GOLD, GOLD_D, GOLD_L, SAGE = C.NAVY, "#B8903A", "#8A6A22", "#F1DE9E", "#7FA17B"
    cx, cy = 0, 30
    t.speed(0); t.hideturtle(); t.tracer(0, 0)

    # 1. starburst rays
    for i in range(24):
        t.penup(); t.goto(cx, cy); t.setheading(i * 15); t.forward(122)
        t.pendown(); t.pensize(5 if i % 2 == 0 else 2); t.color(GOLD_L, GOLD_L); t.forward(118); t.penup()

    # 2. laurel wreath, two sprays that follow the lower half of the medal
    for side in (-1, 1):
        for k in range(8):
            ang = 205 + k * 14 if side < 0 else 335 - k * 14
            x = cx + 112 * math.cos(math.radians(ang))
            y = cy + 112 * math.sin(math.radians(ang))
            _leaf(t, x, y, ang + 90 * (1 if side < 0 else -1) + (25 if side < 0 else -25), 24,
                  "#8FB08A" if k % 2 else "#A9C4A3")

    # 3. medallion
    _disc(t, cx, cy, 104, GOLD_D, GOLD, 3)
    _disc(t, cx, cy, 93, "#0E2342", NAVY, 2)
    _disc(t, cx, cy, 82, GOLD_L, NAVY, 2)

    # 4. big star + one small star per achievement (grey when still locked)
    _star(t, cx, cy + 22, 52, GOLD, GOLD_D)
    _star(t, cx, cy + 22, 24, GOLD_L, GOLD_L)
    for i in range(total):
        x = cx + (i - (total - 1) / 2) * 30
        if i < count:
            _star(t, x, cy - 46, 11, GOLD_L, GOLD_D)
        else:
            _star(t, x, cy - 46, 11, "#4E6483", "#6F85A4")

    # 5. ribbon: tails first, then the band on top
    for sgn in (-1, 1):
        _poly(t, [(sgn * 100, -112), (sgn * 148, -112), (sgn * 128, -132), (sgn * 148, -152),
                  (sgn * 100, -152)], "#0E2342", "#2C4F7C", 2)
    _poly(t, [(-122, -108), (122, -108), (122, -156), (-122, -156)], "#0E2342", NAVY, 2)
    t.goto(0, -141); t.color("#FBF7EC", "#FBF7EC"); t.write(title, align="center", font=("Georgia", 17, "bold"))

    # 6. caption + three small crowning stars
    t.goto(0, -194); t.color(NAVY, NAVY)
    t.write(subtitle if not name else "%s  -  %d of %d unlocked" % (name, count, total),
            align="center", font=("Georgia", 12, "normal"))
    for x in (-34, 0, 34):
        _star(t, x, 180 if x == 0 else 172, 9 if x else 11, GOLD, GOLD_D)


def render_badge(path, count=0, total=4, name=""):
    """Draw the badge headlessly and save a PNG. Returns the path."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    t = PILTurtle((560, 560))
    draw_badge(t, count=count, total=total, name=name[:24])
    t.image().save(path, "PNG", optimize=True)
    return path


def badge_path(count, total, name):
    safe = "".join(ch for ch in name.lower() if ch.isalnum())[:16] or "friend"
    return os.path.join(C.GEN_DIR, "badge_%s_%d_%d.png" % (safe, count, total))


def live():
    """Open the real turtle window (run from a terminal; needs Tkinter)."""
    import turtle
    scr = turtle.Screen()
    scr.setup(600, 600)
    scr.bgcolor("#FBF7EC")
    draw_badge(turtle.Turtle(), count=2, total=4, name="Demo")
    scr.update()
    turtle.done()


if __name__ == "__main__":
    import sys
    if "--live" in sys.argv:
        live()
    else:
        print("wrote", render_badge(os.path.join(C.GEN_DIR, "badge_preview.png"), 2, 4, "Dhara"))
'''),
('state', r'''"""Per-run application context (profile, settings, clock, schedule, log)."""
import datetime as dt
from dataclasses import dataclass

from . import db, logic as L

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None


def now_local(tz_name):
    """Current wall-clock time in the user's chosen time zone (naive datetime)."""
    try:
        return dt.datetime.now(ZoneInfo(tz_name)).replace(tzinfo=None, microsecond=0)
    except Exception:
        return dt.datetime.now().replace(microsecond=0)


@dataclass
class Ctx:
    profile: dict
    settings: dict
    now: dt.datetime
    meds: list
    log: dict
    rstate: dict

    @property
    def today(self):
        return self.now.date()

    @property
    def name(self):
        return self.profile["name"] or "friend"

    @property
    def h24(self):
        return self.settings["h24"] == "1"

    @property
    def window(self):
        return int(self.settings["window"])

    @property
    def snooze(self):
        """The user's saved snooze length in minutes."""
        return L.clamp_snooze(self.settings["snooze_default"])

    def on(self, key):
        return self.settings[key] == "1"


def load():
    profile = db.get_profile()
    now = now_local(profile["tz"])
    return Ctx(profile, db.get_settings(), now, db.list_meds(), db.get_log(), db.get_reminder_state(now.date()))
'''),
('ui', r'''"""Look & feel: theme CSS, Pilly image helpers and small HTML components (no business logic)."""
import base64
import functools
import html
import io
import os
import random

from PIL import Image

from . import config as C
from . import pilly_art

# ------------------------------------------------------------------ images
@functools.lru_cache(maxsize=64)
def pilly_uri(pose, width=440):
    """Pilly as a base64 data URI. Read once from assets/pilly/*.png, resized once, then cached."""
    path = os.path.join(C.PILLY_DIR, "pilly_%s.png" % pose)
    try:
        im = Image.open(path).convert("RGBA")
        im = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "PNG", optimize=True)
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        svg = pilly_art.build_svg(pose)  # asset missing: fall back to the vector version
        return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def pilly_img(pose, height=260, cls="pilly-float", alt="Pilly the capsule doctor"):
    return ('<img class="pilly %s" src="%s" alt="%s" style="max-height:%dpx"/>'
            % (cls, pilly_uri(pose), html.escape(alt), height))


def file_uri(path):
    with open(path, "rb") as fh:
        return "data:image/png;base64," + base64.b64encode(fh.read()).decode()


SPRIG = ('<svg class="sprig" viewBox="0 0 120 120" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">'
         '<g fill="none" stroke="#7FA17B" stroke-width="1.6" stroke-linecap="round">'
         '<path d="M10 112 C34 84 58 56 98 14"/></g>'
         '<g fill="#B9D0B2" stroke="#7FA17B" stroke-width="1.1">'
         '<path d="M30 92 q-16 -6 -18 -22 q16 2 18 22z"/><path d="M44 76 q-18 -2 -24 -18 q18 -2 24 18z"/>'
         '<path d="M58 62 q-14 -10 -12 -26 q16 8 12 26z"/><path d="M72 46 q-16 -4 -20 -20 q16 0 20 20z"/>'
         '<path d="M36 90 q14 -14 30 -10 q-8 16 -30 10z"/><path d="M52 72 q14 -14 30 -10 q-8 16 -30 10z"/>'
         '<path d="M68 56 q14 -14 30 -10 q-8 16 -30 10z"/><path d="M84 36 q12 -12 24 -8 q-6 14 -24 8z"/></g>'
         '<g fill="#C9A24A"><circle cx="100" cy="12" r="3.2"/><circle cx="14" cy="108" r="2.4"/></g></svg>')

# --------------------------------------------------------------------- CSS
def css():
    return """
<style>
:root{--ivory:%(IVORY)s;--ivory-d:%(IVORY_D)s;--card:%(CARD)s;--navy:%(NAVY)s;--navy-d:%(NAVY_D)s;--navy-l:%(NAVY_L)s;
--sage:%(SAGE)s;--sage-l:%(SAGE_L)s;--gold:%(GOLD)s;--gold-l:%(GOLD_L)s;--text:%(TEXT)s;--muted:%(MUTED)s;
--border:%(BORDER)s;--amber:%(AMBER)s;--amber-l:%(AMBER_L)s;--red:%(RED)s;--red-l:%(RED_L)s;--green:%(GREEN)s;--green-l:%(GREEN_L)s;
--serif:Georgia,"Iowan Old Style","Palatino Linotype",Palatino,"Times New Roman",serif;
--sans:"Inter","Segoe UI",system-ui,-apple-system,"Helvetica Neue",Arial,sans-serif;}

/* ---------- page ---------- */
html,body,.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:var(--ivory)!important;color:var(--text);}
/* NB: no `span` here. Streamlit draws its Material icons as <span> ligature text ("home", "medication", ...) in the
   "Material Symbols" font; forcing another font-family on every span turned those icons into plain words. */
.stApp,.stApp p,.stApp li,.stApp label,.stApp input,.stApp textarea,.stApp td,.stApp th{font-family:var(--sans);}
.stApp{overflow-x:hidden;}
[data-testid="stHeader"]{background:transparent!important;}
[data-testid="stMainBlockContainer"],.block-container{max-width:1080px;padding:1.6rem 1.25rem 4rem!important;}
h1,h2,h3,h4,.serif{font-family:var(--serif)!important;color:var(--navy)!important;letter-spacing:.1px;}
h1{font-size:2.8rem!important;line-height:1.15!important;} h2{font-size:2.1rem!important;} h3{font-size:1.65rem!important;}
.stApp p,.stApp li{line-height:1.6;font-size:1.2rem;}
a{color:var(--navy-l);} [data-testid="stMarkdownContainer"] p{margin:0 0 .5rem;}
hr{border-color:var(--border)!important;}

/* ---------- buttons: never clipped, always readable ---------- */
.stButton>button,.stDownloadButton>button,[data-testid="stFormSubmitButton"]>button,
[data-testid="stBaseButton-primary"],[data-testid="stBaseButton-secondary"]{
  width:100%%;min-height:3.2rem;height:auto!important;padding:.55rem 1rem!important;border-radius:12px!important;
  font-family:var(--sans);font-weight:600;font-size:1.15rem;line-height:1.25;white-space:normal!important;
  word-break:normal;overflow:visible!important;text-align:center;box-shadow:0 1px 2px rgba(30,58,95,.10);
  transition:background .15s,box-shadow .15s,transform .05s;}
.stButton>button p,.stDownloadButton>button p,[data-testid="stFormSubmitButton"]>button p{margin:0!important;white-space:normal!important;overflow:visible!important;}
.stButton>button[kind="primary"],.stButton>button[data-testid="stBaseButton-primary"],
[data-testid="stFormSubmitButton"]>button[kind="primaryFormSubmit"],.stDownloadButton>button[kind="primary"]{
  background:var(--navy)!important;color:#fff!important;border:1px solid var(--navy-d)!important;}
.stButton>button[kind="primary"] *,[data-testid="stFormSubmitButton"]>button[kind="primaryFormSubmit"] *{color:#fff!important;}
.stButton>button[kind="secondary"],.stButton>button[data-testid="stBaseButton-secondary"],
.stDownloadButton>button,[data-testid="stFormSubmitButton"]>button[kind="secondaryFormSubmit"]{
  background:#fff!important;color:var(--navy)!important;border:1.5px solid var(--navy)!important;}
.stButton>button[kind="secondary"] *,.stDownloadButton>button *{color:var(--navy)!important;}
.stButton>button:hover,.stDownloadButton>button:hover{box-shadow:0 3px 10px rgba(30,58,95,.18);transform:translateY(-1px);}
.stButton>button[kind="primary"]:hover{background:var(--navy-l)!important;}
.stButton>button:focus-visible{outline:3px solid var(--gold)!important;outline-offset:2px;}
.stButton>button:disabled{opacity:.5;}
.stButton,.stDownloadButton,[data-testid="stFormSubmitButton"]{width:100%%;}

/* ---------- inputs ---------- */
.stTextInput input,.stNumberInput input,.stTextArea textarea,.stTimeInput input,[data-baseweb="select"]>div{
  background:#fff!important;border-radius:10px!important;border:1px solid var(--border)!important;color:var(--text)!important;min-height:3rem;font-size:1.15rem!important;}
.stTextInput input:focus,.stTextArea textarea:focus{border-color:var(--navy-l)!important;box-shadow:0 0 0 2px rgba(63,108,163,.18)!important;}
.stApp label,.stApp [data-testid="stWidgetLabel"] p{color:var(--navy)!important;font-weight:600;font-size:1.15rem;}
[data-testid="stPills"] button,[data-baseweb="button-group"] button{border-radius:999px!important;}
[data-testid="stForm"]{border:1px solid var(--border)!important;border-radius:16px!important;background:var(--card);padding:1.1rem 1.2rem!important;}
[data-testid="stAlert"]{border-radius:12px;}

/* ---------- top navigation tabs ---------- */
.topbar{display:flex;align-items:baseline;gap:.2rem 1rem;flex-wrap:wrap;margin:0 0 .6rem;}
.topbar .brand{font-family:var(--serif);font-size:2.1rem;font-weight:700;color:var(--navy);line-height:1.1;}
.topbar .brand-sub{font-style:italic;color:var(--muted);font-size:1.1rem;}
.topbar .sep{color:var(--gold);font-size:1.5rem;line-height:1;align-self:center;opacity:.8;}
.topbar .streak{display:inline-flex;align-items:center;gap:.4rem;align-self:center;background:var(--navy);color:var(--ivory);
  border:1.5px solid var(--gold);border-radius:999px;padding:.28rem .95rem;font-weight:700;font-size:1.08rem;line-height:1.2;
  white-space:nowrap;box-shadow:0 2px 8px rgba(30,58,95,.22);}
.topbar .streak .n{color:var(--gold-l);font-family:var(--serif);font-size:1.25rem;}
@media (max-width:560px){.topbar .sep{display:none;}.topbar .brand{font-size:1.7rem;}.topbar .streak{font-size:.95rem;padding:.22rem .75rem;}}

/* ---------- reminder pop-up: compact, dark navy, high contrast ---------- */
[data-testid="stDialog"] div[role="dialog"]{width:min(410px,94vw)!important;max-width:410px!important;background:var(--navy-d)!important;
  border:1px solid var(--gold)!important;border-radius:18px!important;}
[data-testid="stDialog"] [data-testid="stVerticalBlock"]{gap:.85rem!important;}
[data-testid="stDialog"] h2{font-size:1.25rem!important;color:#FFF7DD!important;margin:0!important;padding:.1rem 0 .15rem!important;}
[data-testid="stDialog"] button[aria-label="Close"]{color:#FFF7DD!important;}
[data-testid="stDialog"] .rem-med{text-align:center;margin:0;}
[data-testid="stDialog"] .rem-name{font-family:var(--serif);font-size:1.9rem;font-weight:700;color:#FFF7DD;line-height:1.15;}
[data-testid="stDialog"] .rem-time{margin:.85rem 0 0;}
[data-testid="stDialog"] [data-testid="stHorizontalBlock"]{gap:.9rem!important;margin-top:.7rem;padding:0 .35rem;align-items:stretch;}
[data-testid="stDialog"] [data-testid="stHorizontalBlock"] [data-testid="stColumn"]{min-width:0!important;}
[data-testid="stDialog"] [data-testid="stHorizontalBlock"] .stButton,[data-testid="stDialog"] [data-testid="stHorizontalBlock"] .stButton>button{width:100%%;}
[data-testid="stDialog"] .rem-note{color:#E9EDF5;font-size:1.02rem;margin-top:.35rem;font-style:italic;}
[data-testid="stDialog"] [data-testid="stCaptionContainer"],[data-testid="stDialog"] [data-testid="stCaptionContainer"] p{
  color:#F1ECD8!important;text-align:center;font-size:1rem!important;}
[data-testid="stDialog"] [data-testid="stCaptionContainer"]{margin-top:.15rem;padding-bottom:.25rem;}
[data-testid="stDialog"] .stButton>button{min-height:3rem;font-size:1.05rem;padding:.6rem .9rem!important;white-space:nowrap;}
[data-testid="stDialog"] .stButton>button[kind="primary"],[data-testid="stDialog"] .stButton>button[data-testid="stBaseButton-primary"]{
  background:var(--green)!important;border-color:#1E6B33!important;}
[data-testid="stDialog"] .stButton>button[kind="secondary"],[data-testid="stDialog"] .stButton>button[data-testid="stBaseButton-secondary"]{
  background:var(--amber)!important;border-color:#B88500!important;color:#2B2000!important;}
[data-testid="stDialog"] .stButton>button[kind="secondary"] *{color:#2B2000!important;}
.bubble.compact{padding:.55rem .8rem;margin:0;border-width:2px;}
.bubble.compact .big{font-size:1.2rem;line-height:1.25;}
.bubble.compact::after{top:18px;}
.tp-label{font-weight:600;margin:.2rem 0 -.2rem;}
.st-key-topnav{background:var(--card);border:1px solid var(--border);border-radius:20px;padding:.55rem .6rem;
  box-shadow:0 3px 12px rgba(30,58,95,.08);margin-bottom:1.1rem;}
.st-key-topnav [data-testid="stHorizontalBlock"]{flex-wrap:nowrap!important;gap:.4rem!important;}
.st-key-topnav [data-testid="stColumn"],.st-key-topnav [data-testid="column"]{flex:1 1 0!important;min-width:0!important;width:auto!important;}
.st-key-topnav [data-testid="stElementContainer"],.st-key-topnav [data-testid="stButton"],.st-key-topnav .stButton{width:100%% !important;}
.st-key-topnav .stButton>button{width:100%% !important;justify-content:center;}
.st-key-topnav .stButton>button{min-height:3.3rem;border-radius:14px!important;font-size:1.02rem;border-width:1.5px!important;
  padding:.4rem .3rem!important;white-space:nowrap;gap:.35rem;}
.st-key-topnav .stButton>button p,.st-key-topnav .stButton>button div{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin:0;}
@media (max-width:900px){.st-key-topnav .stButton>button{font-size:.88rem;padding:.4rem .15rem!important;gap:.2rem;}}
@media (max-width:640px){.st-key-topnav .stButton>button{font-size:.74rem;}}
.st-key-topnav .stButton>button[kind="primary"],.st-key-topnav .stButton>button[data-testid="stBaseButton-primary"]{
  border-bottom:5px solid var(--gold)!important;box-shadow:0 3px 8px rgba(30,58,95,.25);}
.st-key-topnav .stButton>button[kind="secondary"]:hover,.st-key-topnav .stButton>button[data-testid="stBaseButton-secondary"]:hover{
  background:var(--gold-l)!important;border-color:var(--gold)!important;}

/* ---------- inner tabs and larger widget text ---------- */
[data-baseweb="tab-list"]{gap:.4rem;}
[data-baseweb="tab"]{height:auto!important;padding:.6rem 1.1rem!important;}
[data-baseweb="tab"] p{font-size:1.2rem!important;font-weight:600;color:var(--navy)!important;}
[data-baseweb="tab-highlight"]{background:var(--gold)!important;height:3px!important;}
[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p{font-size:1.02rem!important;}
[data-testid="stExpander"] summary p{font-size:1.2rem!important;font-weight:600;}
[data-testid="stAlert"] p{font-size:1.12rem!important;}
[data-baseweb="select"] div,[data-baseweb="select"] span,[data-baseweb="popover"] li{font-size:1.12rem!important;}
[data-testid="stRadio"] label p,[data-testid="stToggle"] label p{font-size:1.15rem!important;}
[data-testid="stPills"] button p{font-size:1.08rem!important;}
[data-testid="stDataFrame"]{font-size:1.1rem;}

/* ---------- cards ---------- */
[class*="st-key-card_"]{background:var(--card);border:1px solid var(--border);border-radius:18px;padding:1rem 1.15rem;
  box-shadow:0 2px 10px rgba(30,58,95,.07);margin-bottom:.8rem;position:relative;}
[class*="st-key-card_"] [class*="st-key-card_"]{box-shadow:none;background:#fff;}
.card-title{font-family:var(--serif);color:var(--navy);font-size:1.5rem;margin:0 0 .4rem;font-weight:700;}
.muted{color:var(--muted);font-size:1.08rem;} .small{font-size:1.02rem;}
.sprig{position:absolute;right:6px;top:6px;width:84px;height:84px;opacity:.55;pointer-events:none;}
.gold-rule{height:2px;border:0;background:linear-gradient(90deg,transparent,var(--gold),transparent);margin:.7rem 0 1rem;opacity:.7;}

/* ---------- hero ---------- */
.hero{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:1rem;position:relative;overflow:hidden;
  background:linear-gradient(135deg,#FFFDF5 0%%,#F6EDD3 100%%);border:1px solid var(--border);border-radius:22px;
  padding:1.2rem 1.6rem;box-shadow:0 4px 16px rgba(30,58,95,.08);margin-bottom:1rem;}
.hero .txt{flex:1 1 280px;min-width:0;position:relative;z-index:1;font-size:1.3rem;}
.hero h1,.hero h2{margin:.1rem 0 .3rem!important;}
.hero .art{flex:0 0 auto;text-align:center;margin:0 auto;}
.hero .art img{width:auto;height:auto;max-width:100%%;}
.eyebrow{color:var(--gold);font-weight:700;letter-spacing:.14em;font-size:.92rem;text-transform:uppercase;}

/* ---------- Pilly + bubble ---------- */
img.pilly{display:block;margin:0 auto;filter:drop-shadow(0 8px 10px rgba(30,58,95,.18));}
.pilly-float{animation:pfloat 4.2s ease-in-out infinite;} .pilly-still{animation:none;}
.pilly-jump{animation:pjump .85s ease-in-out 3;}
@keyframes pfloat{0%%,100%%{transform:translateY(0)}50%%{transform:translateY(-6px)}}
@keyframes pjump{0%%,100%%{transform:translateY(0) scale(1,1)}30%%{transform:translateY(-26px) scale(.98,1.03)}60%%{transform:translateY(0) scale(1.03,.97)}}
.bubble{position:relative;background:#fff;border:2px solid var(--navy);border-radius:20px;padding:.9rem 1.1rem;margin:.2rem 0 1rem;
  box-shadow:0 3px 10px rgba(30,58,95,.10);animation:fadeup .5s ease both;}
.bubble::after{content:"";position:absolute;left:-12px;top:26px;width:20px;height:20px;background:#fff;border-left:2px solid var(--navy);
  border-bottom:2px solid var(--navy);transform:rotate(45deg);}
.bubble.top::after{left:42px;top:auto;bottom:-12px;border-left:0;border-bottom:2px solid var(--navy);border-right:2px solid var(--navy);}
.bubble .big{font-family:var(--serif);color:var(--navy);font-size:1.85rem;font-weight:700;line-height:1.25;margin:0;}
.bubble .sm{margin:.35rem 0 0;color:var(--text);}
@keyframes fadeup{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
@media (prefers-reduced-motion:reduce){.pilly-float,.pilly-jump,.bubble,.confetti i,.fstar,.flash.taken img,.flash .spk{animation:none!important}.flash .spk{opacity:1}}

/* ---------- onboarding steps ---------- */
.steps{display:flex;gap:.5rem;align-items:center;justify-content:center;margin:.2rem 0 1rem;flex-wrap:wrap;}
.steps .s{display:flex;align-items:center;gap:.4rem;font-size:1.02rem;color:var(--muted);}
.steps .dot{width:26px;height:26px;border-radius:50%%;border:2px solid var(--border);display:flex;align-items:center;justify-content:center;
  font-weight:700;background:#fff;color:var(--muted);}
.steps .s.on .dot{background:var(--navy);border-color:var(--navy);color:#fff;} .steps .s.on{color:var(--navy);font-weight:700;}
.steps .s.done .dot{background:var(--sage);border-color:var(--sage);color:#fff;}
.steps .bar{width:22px;height:2px;background:var(--border);}

/* ---------- stats / status ---------- */
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:.8rem;margin:.2rem 0 1rem;}
.stat{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:.8rem 1rem;box-shadow:0 2px 8px rgba(30,58,95,.06);
  text-align:center;min-width:0;}
.stat .n{font-family:var(--serif);font-size:2.5rem;font-weight:700;color:var(--navy);line-height:1.1;}
.stat .l{font-size:1.05rem;color:var(--muted);margin-top:.15rem;}
.stat.g{border-top:4px solid var(--green);} .stat.y{border-top:4px solid var(--amber);} .stat.r{border-top:4px solid var(--red);}
.stat.g .n,.stat.g .l .ic{color:#1F6B33;} .stat.y .n,.stat.y .l .ic{color:#9A7000;} .stat.r .n,.stat.r .l .ic{color:#B02A22;}
.stat.n0{border-top:4px solid var(--navy);} .stat.gold{border-top:4px solid var(--gold);}
.ic{width:1.05em;height:1.05em;flex:0 0 auto;vertical-align:-.14em;}
.stat .l{display:flex;align-items:center;justify-content:center;gap:.35rem;flex-wrap:wrap;}
.banner .ic{width:1.35rem;height:1.35rem;margin-top:.12rem;color:var(--navy);}
.banner .ico-wrap{display:inline-flex;flex:0 0 auto;}
.steps .dot .ic{width:.85rem;height:.85rem;}
.ach .ico .ic{width:1.7rem;height:1.7rem;}
.fstar .ic{width:1.4rem;height:1.4rem;}
.pill{display:inline-flex;align-items:center;gap:.3rem;border-radius:999px;padding:.22rem .8rem;font-size:1.02rem;font-weight:700;white-space:nowrap;}
.pill.taken{background:var(--green-l);color:#14532D;border:1px solid #8CC79A;}
.pill.upcoming{background:var(--amber-l);color:#6B4E00;border:1px solid #E6C94F;}
.pill.missed{background:var(--red-l);color:#8E1B16;border:1px solid #E39A93;}
/* status colour coding on medicine cards: GREEN = taken, YELLOW = upcoming, RED = missed */
[class*="st-key-card_dose_taken_"],[class*="st-key-card_rem_taken_"]{border-left:7px solid var(--green);}
[class*="st-key-card_dose_upcoming_"],[class*="st-key-card_rem_upcoming_"]{border-left:7px solid var(--amber);}
[class*="st-key-card_dose_missed_"],[class*="st-key-card_rem_missed_"]{border-left:7px solid var(--red);}
.dose{display:flex;flex-wrap:wrap;align-items:center;gap:.5rem .8rem;}
.dose .nm{font-weight:700;color:var(--text);font-size:1.5rem;} .dose .tm{color:var(--muted);font-size:1.25rem;}
.dose .nt{flex-basis:100%%;color:var(--muted);font-size:1.08rem;font-style:italic;}
.ring{display:flex;align-items:center;gap:1rem;flex-wrap:wrap;}
.ring svg{flex:0 0 auto;}
.banner{background:var(--gold-l);border:1px solid #E6D08A;border-radius:14px;padding:.7rem 1rem;color:var(--navy-d);display:flex;gap:.6rem;align-items:flex-start;font-size:1.15rem;}
.banner.due{background:var(--amber-l);border-color:#E9CF7B;}

/* ---------- bar chart ---------- */
.chart{display:flex;align-items:flex-end;gap:.55rem;height:260px;padding:.4rem .2rem 0;}
.chart .col{flex:1 1 0;min-width:0;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%%;}
.chart .bar{width:100%%;max-width:64px;border-radius:10px 10px 0 0;background:linear-gradient(180deg,#5D84B6,var(--navy));min-height:6px;}
.chart .bar.hi{background:linear-gradient(180deg,#7CC38D,var(--green));} .chart .bar.lo{background:linear-gradient(180deg,#E58A82,var(--red));}
.chart .bar.none{background:repeating-linear-gradient(45deg,#EFE8D2,#EFE8D2 5px,#F8F3E3 5px,#F8F3E3 10px);min-height:14px;}
.chart .v{font-size:1rem;font-weight:700;color:var(--navy);margin-bottom:.2rem;white-space:nowrap;}
.chart .d{font-size:1.1rem;margin-top:.35rem;color:var(--muted);} .chart .d.today{color:var(--navy);font-weight:800;border-bottom:2px solid var(--gold);}
.chart .sub{font-size:.9rem;color:var(--muted);}

/* ---------- achievements ---------- */
.ach{display:flex;gap:.9rem;align-items:center;}
.ach .ico{flex:0 0 52px;height:52px;border-radius:50%%;display:flex;align-items:center;justify-content:center;font-size:1.5rem;
  background:var(--gold-l);border:2px solid var(--gold);color:var(--gold);}
.ach.locked .ico{background:#EEE9DA;border-color:#CFC7B0;color:#B7AF99;filter:grayscale(1);} .ach.locked .t{color:var(--muted);}
.ach .t{font-family:var(--serif);font-weight:700;color:var(--navy);font-size:1.4rem;}
.celebrate{position:relative;overflow:hidden;text-align:center;background:linear-gradient(135deg,#FFF9E3,#F5E6B4);border:1px solid #E6D08A;
  border-radius:22px;padding:1rem 1rem 1.2rem;margin-bottom:1rem;box-shadow:0 6px 22px rgba(184,144,58,.25);}
.celebrate h2{margin:.2rem 0!important;}
.fstar{position:absolute;color:var(--gold);animation:fl 3s ease-in-out infinite;font-size:1.4rem;}
@keyframes fl{0%%,100%%{transform:translateY(0) rotate(0);opacity:.9}50%%{transform:translateY(-14px) rotate(20deg);opacity:.5}}
.confetti{position:fixed;inset:0;pointer-events:none;overflow:hidden;z-index:50;}
.confetti i{position:absolute;top:-16px;width:9px;height:14px;opacity:0;animation:cf 3.4s ease-in 1 forwards;}
@keyframes cf{0%%{transform:translateY(0) rotate(0);opacity:1}100%%{transform:translateY(105vh) rotate(720deg);opacity:0}}

/* ---------- flash message ---------- */
.flash{display:flex;align-items:center;gap:1rem;flex-wrap:wrap;background:var(--sage-l);border:1px solid #BFD3B8;border-radius:18px;
  padding:.5rem 1.1rem;margin-bottom:1rem;animation:fadeup .4s ease both;}
.flash.info{background:#fff;border-color:var(--border);} .flash.snooze{background:var(--amber-l);border-color:#E9CF7B;}
.flash img{height:118px;width:auto;flex:0 0 auto;} .flash .ft{flex:1 1 220px;min-width:0;}
.flash.taken{position:relative;overflow:hidden;background:var(--green-l);border-color:#8CC79A;}
.flash.taken img{height:150px;transform-origin:50%% 90%%;animation:thumbpop .7s cubic-bezier(.3,1.6,.5,1) both,thumbbob 1.5s ease-in-out .7s 2;}
@keyframes thumbpop{0%%{transform:scale(.4) rotate(-12deg);opacity:0}60%%{transform:scale(1.12) rotate(6deg);opacity:1}100%%{transform:scale(1) rotate(0);opacity:1}}
@keyframes thumbbob{0%%,100%%{transform:translateY(0)}50%%{transform:translateY(-6px)}}
.flash .spk{position:absolute;color:var(--gold);opacity:0;pointer-events:none;animation:twinkle 1.6s ease-in-out 2 both;}
.flash .spk .ic{width:1.15rem;height:1.15rem;}
@keyframes twinkle{0%%{opacity:0;transform:scale(.3) rotate(0)}40%%{opacity:1;transform:scale(1.2) rotate(20deg)}100%%{opacity:0;transform:scale(.6) rotate(60deg) translateY(-10px)}}
.flash .fh{font-family:var(--serif);font-weight:700;color:var(--navy);font-size:1.55rem;margin:0;}

/* ---------- tips / legal ---------- */
.tip{display:flex;gap:.8rem;align-items:center;background:#fff;border:1px dashed var(--gold);border-radius:16px;padding:.7rem 1rem;margin:.6rem 0;}
.tip img{height:84px;width:auto;flex:0 0 auto;} .tip .tt{font-size:1.15rem;}
.legal{font-size:.98rem;color:var(--muted);border-top:1px solid var(--border);padding-top:.7rem;margin-top:1.2rem;line-height:1.5;}

/* ---------- responsive ---------- */
@media (max-width:760px){
  [data-testid="stMainBlockContainer"],.block-container{padding:1rem .8rem 3rem!important;}
  h1{font-size:2.1rem!important;} .hero{padding:1rem;} .hero .art img{max-height:190px!important;}
  .bubble .big{font-size:1.5rem;} .chart{height:210px;gap:.3rem;} .chart .v{font-size:.82rem;}
  .bubble::after{left:34px;top:auto;bottom:-12px;border-left:0;border-bottom:2px solid var(--navy);border-right:2px solid var(--navy);}
}
@media (max-width:420px){.grid{grid-template-columns:repeat(2,1fr);}.sprig{display:none;}}
</style>
""" % {k: getattr(C, k) for k in ("IVORY", "IVORY_D", "CARD", "NAVY", "NAVY_D", "NAVY_L", "SAGE", "SAGE_L", "GOLD", "GOLD_L",
                                  "TEXT", "MUTED", "BORDER", "AMBER", "AMBER_L", "RED", "RED_L", "GREEN", "GREEN_L")}


# --------------------------------------------------------------- components
def esc(s):
    return html.escape(str(s), quote=True)


# Small inline SVG icons. They are real drawings, not text, so they can never show up as raw character codes
# or as an icon's name, and they do not depend on any font being installed.
_ICONS = {
    "check": '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    "clock": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    "cross": '<path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/>',
    "bell": '<path d="M6 16.5V11a6 6 0 0 1 12 0v5.5l1.5 1.5h-15z"/><path d="M10 20.5a2 2 0 0 0 4 0"/>',
    "spark": '<path d="M12 3l1.8 5.7 5.7 1.8-5.7 1.8L12 18l-1.8-5.7-5.7-1.8 5.7-1.8z"/>',
    "star": '<path d="M12 3.5l2.6 5.5 5.9.7-4.4 4 1.2 5.8-5.3-2.9-5.3 2.9 1.2-5.8-4.4-4 5.9-.7z"/>',
    "moon": '<path d="M19 14.5A7.5 7.5 0 0 1 9.5 5a7.5 7.5 0 1 0 9.5 9.5z"/>',
    "leaf": '<path d="M5 19c0-8 5-13 14-14 0 9-5 14-13 14z"/><path d="M5 19c3-4 6-7 10-9"/>',
}


def icon(name):
    """Inline SVG icon (check, clock, cross, bell, spark, star, moon, leaf). Inherits the surrounding text colour."""
    return ('<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">%s</svg>' % _ICONS[name])


def hero(title, text, pose, eyebrow="", height=230, cls="pilly-float"):
    return ('<div class="hero"><div class="txt">%s<h1>%s</h1><div>%s</div></div><div class="art">%s</div></div>'
            % ('<div class="eyebrow">%s</div>' % esc(eyebrow) if eyebrow else "", title, text, pilly_img(pose, height, cls)))


def bubble(big, small="", tail="left"):
    return '<div class="bubble %s"><p class="big">%s</p>%s</div>' % (
        "top" if tail == "top" else "", big, '<p class="sm">%s</p>' % small if small else "")


def steps(current, labels):
    out = []
    for i, lab in enumerate(labels):
        cls = "done" if i < current else "on" if i == current else ""
        out.append('<div class="s %s"><span class="dot">%s</span><span>%s</span></div>' % (cls, icon("check") if i < current else i + 1, esc(lab)))
        if i < len(labels) - 1:
            out.append('<span class="bar"></span>')
    return '<div class="steps">%s</div>' % "".join(out)


def pill(status):
    sym = {"taken": "check", "upcoming": "clock", "missed": "cross"}[status]
    lab = {"taken": "Taken", "upcoming": "Upcoming", "missed": "Missed"}[status]
    return '<span class="pill %s">%s %s</span>' % (status, icon(sym), lab)


def stat(n, label, cls="", icon_name=None):
    """One number tile. `label` is plain text (it is escaped); the optional icon is drawn separately."""
    return ('<div class="stat %s"><div class="n">%s</div><div class="l">%s<span>%s</span></div></div>'
            % (cls, n, icon(icon_name) if icon_name else "", esc(label)))


def note(icon_name, html_text, style=""):
    """Banner row with a drawn icon followed by text that is already safe HTML."""
    return ('<div class="banner"%s><span class="ico-wrap">%s</span><span>%s</span></div>'
            % (' style="%s"' % style if style else "", icon(icon_name), html_text))


def ring(pct, label="Daily adherence", size=132):
    r, circ = 52, 2 * 3.14159265 * 52
    off = circ * (1 - (pct or 0) / 100.0)
    txt = "&ndash;" if pct is None else "%d%%" % round(pct)
    return ('<svg width="%d" height="%d" viewBox="0 0 132 132" role="img" aria-label="%s %s">'
            '<circle cx="66" cy="66" r="%d" fill="none" stroke="#E8E2CE" stroke-width="12"/>'
            '<circle cx="66" cy="66" r="%d" fill="none" stroke="%s" stroke-width="12" stroke-linecap="round" '
            'stroke-dasharray="%.1f" stroke-dashoffset="%.1f" transform="rotate(-90 66 66)"/>'
            '<text x="66" y="68" text-anchor="middle" font-family="Georgia,serif" font-size="28" font-weight="700" fill="%s">%s</text>'
            '</svg>'
            % (size, size, esc(label), "n/a" if pct is None else "%d percent" % round(pct), r, r, C.SAGE, circ, off,
               C.NAVY, txt))


def bar_chart(df, today):
    cols = []
    for _i, r in df.iterrows():
        pct = r["adherence"]
        is_today = r["date"] == today
        if pct != pct or pct is None:  # NaN
            bar, val, cls = '<div class="bar none" style="height:14%"></div>', "&ndash;", ""
        else:
            cls = "hi" if pct >= 90 else "lo" if pct < 60 else ""
            bar = '<div class="bar %s" style="height:%d%%"></div>' % (cls, max(4, min(100, round(pct)) * 0.78))
            val = "%d%%" % round(pct)
        cols.append('<div class="col" title="%s: %d taken, %d missed"><div class="v">%s</div>%s<div class="d %s">%s</div>'
                    '<div class="sub">%d/%d</div></div>' % (r["day"], r["taken"], r["missed"], val, bar,
                                                            "today" if is_today else "", r["day"], r["taken"], r["due"]))
    return '<div class="chart" role="img" aria-label="Seven day adherence chart">%s</div>' % "".join(cols)


def confetti(n=38, seed=None):
    rnd = random.Random(seed)
    cols = [C.NAVY, C.GOLD, C.SAGE, "#F1DE9E", "#6F93C4", "#E3B7A0"]
    bits = []
    for _ in range(n):
        bits.append('<i style="left:%d%%;background:%s;animation-delay:%.2fs;animation-duration:%.1fs;border-radius:%s"></i>'
                    % (rnd.randint(1, 98), rnd.choice(cols), rnd.uniform(0, 1.2), rnd.uniform(2.6, 4.0),
                       "50%" if rnd.random() < .3 else "2px"))
    return '<div class="confetti" aria-hidden="true">%s</div>' % "".join(bits)


def celebration(name, headline, pose="achievement"):
    stars = "".join('<span class="fstar" style="left:%d%%;top:%d%%;animation-delay:%.1fs">%s</span>' % (x, y, d, icon("spark"))
                    for x, y, d in ((8, 14, 0), (88, 18, .6), (16, 66, 1.1), (80, 62, .3), (50, 6, .9)))
    return ('<div class="celebrate">%s%s%s<div class="eyebrow">Achievement unlocked</div><h2>%s</h2>'
            '<div class="muted">Pilly is very proud of you, %s.</div></div>'
            % (confetti(seed=hash(headline) & 0xFFFF), stars, pilly_img(pose, 250, "pilly-jump"), esc(headline), esc(name or "friend")))


def tip_box(text, pose="tips"):
    return '<div class="tip"><img src="%s" alt="Pilly with reading glasses"/><div class="tt">%s</div></div>' % (pilly_uri(pose, 200), text)


def legal():
    return '<div class="legal">%s</div>' % esc(C.DISCLAIMER)


def flash(kind, text, heading=""):
    pose = {"taken": "thumbsup", "snoozed": "reminder", "welcome": "welcome"}.get(kind)
    img = '<img src="%s" alt="Pilly giving a thumbs up"/>' % pilly_uri(pose, 220) if pose else ""
    cls = {"snoozed": "snooze", "info": "info", "taken": "taken"}.get(kind, "")
    sparks = ""
    if kind == "taken":   # a few CSS-only sparkles (transform/opacity only, so they stay smooth)
        sparks = "".join('<span class="spk" style="left:%d%%;top:%d%%;animation-delay:%.2fs">%s</span>'
                         % (x, y, d, icon("star" if i % 2 else "spark"))
                         for i, (x, y, d) in enumerate(((5, 12, .25), (28, 68, .55), (60, 10, .45), (90, 28, .15), (82, 74, .75), (45, 42, .9))))
    return '<div class="flash %s">%s%s<div class="ft">%s<div>%s</div></div></div>' % (
        cls, sparks, img, '<p class="fh">%s</p>' % heading if heading else "", text)
'''),
('reminders', r'''"""In-app reminders: background poller (a Streamlit fragment), the Pilly pop-up dialog, dose actions and the snooze picker.

Honest limitation: Streamlit only runs code while a browser tab is connected. These reminders fire while
MedTimer is open (the tab may be in the background); they cannot fire when the tab/browser is closed.
"""
import base64
import datetime as dt
import functools
import random
import time

import streamlit as st
import streamlit.components.v1 as components

from . import audio, config as C, db, logic as L, state, ui

POLL_SECONDS = 15


@functools.lru_cache(maxsize=16)
def _wav_b64(name, volume):
    return base64.b64encode(audio.make_wav_cached(name, volume)).decode("ascii")


def play_hidden(name, volume):
    """Play a sound in the background. It runs in a tiny invisible frame (no controls, no player on screen) and starts itself
    with script, which browsers allow once the page has been clicked. A fresh id on every call makes it play again each time."""
    html = ('<audio id="a" src="data:audio/wav;base64,%s" preload="auto"></audio>'
            '<script>/* %d */var a=document.getElementById("a");a.volume=1;var p=a.play();'
            'if(p&&p.catch){p.catch(function(){document.addEventListener("click",function(){a.play();},{once:true});});}</script>'
            % (_wav_b64(name, int(volume)), time.time_ns()))
    components.html(html, height=0)


CUSTOM = "Custom"
SNOOZE_OPTIONS = list(C.SNOOZE_CHOICES) + [CUSTOM]
PICKER_KEYS = ("rem_snz", "ob_snz")   # snooze pickers that live on pages (the pop-up has its own)


# ------------------------------------------------------------------ actions
def _ctx_now():
    p = db.get_profile()
    return p, state.now_local(p["tz"])


def take_dose(med_id, source="checklist"):
    p, now = _ctx_now()
    med = db.get_med(med_id)
    if not med:
        return
    db.mark_taken(med_id, now.date(), now.strftime("%H:%M"))
    db.add_event(now, med, med["time"], "taken", source)
    st.session_state["flash"] = {"kind": "taken", "med": med["name"],
                                 "text": random.choice(L.TAKEN_MESSAGES).format(n=p["name"] or "friend")}
    st.session_state.pop("dialog_open", None)


def undo_dose(med_id):
    _p, now = _ctx_now()
    med = db.get_med(med_id)
    if med:
        db.unmark_taken(med_id, now.date())
        db.add_event(now, med, med["time"], "undone", "marked as not taken")
        st.session_state["flash"] = {"kind": "info", "text": "%s is no longer marked as taken." % med["name"]}


def snooze_dose(med_id, minutes):
    """Postpone today's reminder by `minutes`. The new time is stored in the database, so the poller
    really fires the reminder again then. The length is also saved as the user's snooze preference."""
    _p, now = _ctx_now()
    med = db.get_med(med_id)
    if not med:
        return
    minutes = L.clamp_snooze(minutes)
    until = min(now + dt.timedelta(minutes=minutes), dt.datetime.combine(now.date(), dt.time(23, 59)))
    db.snooze(med_id, now.date(), until)
    db.set_setting("snooze_default", minutes)
    db.add_event(now, med, med["time"], "snoozed", "for %d minutes, until %s" % (minutes, until.strftime("%H:%M")))
    h24 = db.get_settings()["h24"] == "1"
    st.session_state["flash"] = {"kind": "snoozed", "text": "Snoozed %s for %d minutes. I'll remind you again at %s."
                                 % (med["name"], minutes, L.fmt_time(until.strftime("%H:%M"), h24))}
    st.session_state.pop("dialog_open", None)
    for key in PICKER_KEYS:                       # pickers on other pages re-read the saved value
        for suffix in ("_c", "_m"):
            st.session_state.pop(key + suffix, None)


# ------------------------------------------------------------ snooze picker
def _label(option):
    return CUSTOM if option == CUSTOM else "%d min" % option


def picked_minutes(key):
    ss = st.session_state
    choice = ss.get(key + "_c")
    return L.clamp_snooze(ss.get(key + "_m") if choice == CUSTOM else choice)


def _persist(key):
    db.set_setting("snooze_default", picked_minutes(key))


def remind_at(ctx, minutes):
    """Clock time (as text) at which a snooze of `minutes`, started now, would fire."""
    return L.fmt_time((ctx.now + dt.timedelta(minutes=minutes)).strftime("%H:%M"), ctx.h24)


def snooze_picker(ctx, key, persist=False):
    """Preset choices (5/10/15/20/30) plus a Custom box for any number of minutes.
    persist=True saves every change as the new default; the pop-up saves it when Snooze is pressed."""
    ss = st.session_state
    if key + "_c" not in ss:                      # fresh picker: start from the saved preference
        saved = ctx.snooze
        ss[key + "_c"] = saved if saved in C.SNOOZE_CHOICES else CUSTOM
        ss[key + "_m"] = saved if saved not in C.SNOOZE_CHOICES else 25
    ss.setdefault(key + "_m", 25)
    cb = {"on_change": _persist, "args": (key,)} if persist else {}
    st.radio("Snooze for", SNOOZE_OPTIONS, key=key + "_c", horizontal=True, format_func=_label, **cb)
    if ss[key + "_c"] == CUSTOM:
        st.number_input("Custom snooze (minutes)", min_value=C.SNOOZE_MIN, max_value=C.SNOOZE_MAX, step=1,
                        key=key + "_m", **cb)
    return picked_minutes(key)


# ------------------------------------------------------------------ pop-up
@st.dialog("Medicine reminder")
def reminder_dialog(med_id, day_iso):
    med = db.get_med(med_id)
    if not med:
        st.rerun()
        return
    ctx = state.load()
    if (day_iso, med_id) in ctx.log:       # already taken elsewhere
        st.success("Already marked as taken.")
        return
    played = st.session_state.setdefault("_played", set())
    first = (med_id, day_iso, ctx.rstate.get(med_id, {}).get("fired_at")) not in played
    played.add((med_id, day_iso, ctx.rstate.get(med_id, {}).get("fired_at")))
    minutes = ctx.snooze                      # the length the user chose in set-up / Reminders: no picker here
    pic, say = st.columns([1, 2.1], vertical_alignment="center", gap="small")
    pic.markdown('<div style="text-align:center">%s</div>' % ui.pilly_img("reminder", 118, "pilly-float"), unsafe_allow_html=True)
    say.markdown('<div class="bubble compact"><p class="big">Hi %s! Time for your medicine.</p></div>' % ui.esc(ctx.name),
                 unsafe_allow_html=True)
    notes = '<div class="rem-note">%s</div>' % ui.esc(med["notes"]) if med["notes"] else ""
    st.markdown('<div class="rem-med"><div class="rem-name">%s</div><div class="rem-time"><span class="pill upcoming">%s %s</span></div>%s</div>'
                % (ui.esc(med["name"]), ui.icon("clock"), L.fmt_time(med["time"], ctx.h24), notes), unsafe_allow_html=True)
    a, b = st.columns(2, gap="small")
    with a:
        if st.button("Mark as Taken", type="primary", key="dlg_take_%d" % med_id):
            take_dose(med_id, "pop-up")
            st.rerun()
    with b:
        if st.button("Snooze %d min" % minutes, key="dlg_later_%d" % med_id):
            snooze_dose(med_id, minutes)
            st.rerun()
    st.caption("Pilly will remind you again at %s." % remind_at(ctx, minutes))
    if first and ctx.on("audio"):
        play_hidden(ctx.settings["sound"], ctx.settings["volume"])


# ------------------------------------------------------------------ poller
@st.fragment(run_every=POLL_SECONDS)
def poller():
    """Runs every POLL_SECONDS while the page is open. Claims due reminders in the database
    (so each one fires exactly once) and asks the full app to rerun only when something changed."""
    ss = st.session_state
    ctx = state.load()
    opened = ss.get("dialog_open")
    if opened and (ctx.now - opened) < dt.timedelta(minutes=3):
        return  # a pop-up is on screen: don't pull the app out from under it
    sig = (ctx.today.isoformat(), len(ctx.meds),
           tuple((L.status_of(m, ctx.today, ctx.now, ctx.log, ctx.window, ctx.rstate),
                  L.is_due_now(m, ctx.today, ctx.now, ctx.log, ctx.window, ctx.rstate))
                 for m in L.doses_for_day(ctx.meds, ctx.today)))
    changed = ss.get("_sig") not in (None, sig)
    ss["_sig"] = sig
    if ctx.on("reminders_enabled"):
        for med, kind in L.pending_reminders(ctx.meds, ctx.today, ctx.now, ctx.log, ctx.rstate, ctx.window):
            claimed = db.mark_fired(med["id"], ctx.today, ctx.now) if kind == "new" else db.refire_snoozed(med["id"], ctx.today, ctx.now)
            if claimed:
                db.add_event(ctx.now, med, med["time"], "reminder shown" if kind == "new" else "reminded again")
                ss.setdefault("popup_queue", []).append(med["id"])
                ss["_from_poller"] = True
                st.rerun()
    if changed:
        ss["_from_poller"] = True
        st.rerun()
'''),
('screens.medicines', r'''"""My Medicines screen + the reusable add / edit / delete manager (also used in onboarding)."""
import datetime as dt

import streamlit as st

from .. import config as C, db, logic as L, ui


def _time_str(t):
    return "%02d:%02d" % (t.hour, t.minute)


def time_picker(label, value, key):
    """Scheduled-time entry with three dropdowns - Hour (1-12), Minute and AM/PM - so nobody has to read a 24-hour clock.
    Returns a datetime.time (24-hour internally, as the rest of the app expects)."""
    h12 = value.hour % 12 or 12
    st.markdown('<div class="tp-label">%s</div>' % label, unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 1], gap="small")
    hh = c1.selectbox("Hour", list(range(1, 13)), index=h12 - 1, key=key + "_h", format_func=lambda v: "%d" % v)
    mm = c2.selectbox("Minute", list(range(60)), index=value.minute, key=key + "_m", format_func=lambda v: "%02d" % v)
    ap = c3.selectbox("AM / PM", ["AM", "PM"], index=0 if value.hour < 12 else 1, key=key + "_ap")
    return dt.time((hh % 12) + (12 if ap == "PM" else 0), mm)


def _days_idx(labels):
    return [C.DAYS.index(d) for d in (labels or [])]


def _flash(kind, text):
    st.session_state["flash"] = {"kind": kind, "text": text}


def _set(key, val):
    st.session_state[key] = val


def _clear(*keys):
    for k in keys:
        st.session_state.pop(k, None)


def med_manager(ctx, prefix, expand_add=None):
    ss = st.session_state
    n = ss.get(prefix + "_n", 0)                 # bumping n gives the add-form fresh, empty widgets
    meds = db.list_meds()
    if expand_add is None:
        expand_add = not meds

    # ---------------------------------------------------------------- add
    with st.expander("Add a medicine", expanded=expand_add):
        with st.form("%s_add_%d" % (prefix, n), border=False):
            name = st.text_input("Medicine name", key="%s_name_%d" % (prefix, n), max_chars=60,
                                 placeholder="e.g. the name on your prescription label")
            time_v = time_picker("Scheduled time", dt.time(8, 0), "%s_time_%d" % (prefix, n))
            days = st.pills("Days", C.DAYS, selection_mode="multi", default=C.DAYS, key="%s_days_%d" % (prefix, n))
            notes = st.text_input("Medicine details (optional)", key="%s_notes_%d" % (prefix, n), max_chars=200,
                                  placeholder="e.g. dose and instructions, as written on your prescription")
            go = st.form_submit_button("Add medicine", type="primary")
        if go:
            try:
                db.add_med(name, _time_str(time_v), _days_idx(days), notes, today=ctx.today)
                ss[prefix + "_n"] = n + 1
                _flash("info", "Added %s." % name.strip())
                st.rerun()
            except ValueError as e:
                st.error(str(e))

    # --------------------------------------------------------------- list
    meds = db.list_meds()
    st.markdown('<div class="card-title" style="margin-top:.6rem">Saved medicines <span class="muted small">(%d)</span></div>' % len(meds),
                unsafe_allow_html=True)
    if not meds:
        st.info("No medicines yet. Add your first one above.")
    editing, deleting = ss.get(prefix + "_edit"), ss.get(prefix + "_del")
    for m in meds:
        with st.container(key="card_%s_med_%d" % (prefix, m["id"])):
            if editing == m["id"]:
                with st.form("%s_editform_%d" % (prefix, m["id"]), border=False):
                    st.markdown('<div class="card-title">Edit medicine</div>', unsafe_allow_html=True)
                    e_name = st.text_input("Medicine name", value=m["name"], max_chars=60, key="%s_en_%d" % (prefix, m["id"]))
                    e_time = time_picker("Scheduled time", L.to_time(m["time"]), "%s_et_%d" % (prefix, m["id"]))
                    e_days = st.pills("Days", C.DAYS, selection_mode="multi", default=[C.DAYS[i] for i in m["days"]],
                                      key="%s_ed_%d" % (prefix, m["id"]))
                    e_notes = st.text_input("Medicine details (optional)", value=m["notes"], max_chars=200, key="%s_eo_%d" % (prefix, m["id"]))
                    c1, c2 = st.columns(2)
                    save = c1.form_submit_button("Save changes", type="primary")
                    cancel = c2.form_submit_button("Cancel")
                if cancel:
                    _clear(prefix + "_edit")
                    st.rerun()
                if save:
                    try:
                        db.update_med(m["id"], e_name, _time_str(e_time), _days_idx(e_days), e_notes)
                        _clear(prefix + "_edit")
                        _flash("info", "Saved changes to %s." % e_name.strip())
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
            else:
                note = '<div class="nt">%s</div>' % ui.esc(m["notes"]) if m["notes"] else ""
                c1, c2 = st.columns([3, 2], vertical_alignment="center")
                c1.markdown('<div class="dose"><span class="nm">%s</span><span class="tm">%s &middot; %s</span>%s</div>'
                            % (ui.esc(m["name"]), L.fmt_time(m["time"], ctx.h24), L.fmt_days(m["days"]), note), unsafe_allow_html=True)
                with c2:
                    b1, b2 = st.columns(2)
                    b1.button("Edit", key="%s_editbtn_%d" % (prefix, m["id"]), on_click=_set, args=(prefix + "_edit", m["id"]))
                    b2.button("Delete", key="%s_delbtn_%d" % (prefix, m["id"]), on_click=_set, args=(prefix + "_del", m["id"]))
                if deleting == m["id"]:
                    st.warning("Delete **%s**? Its schedule and history will be removed." % m["name"])
                    d1, d2 = st.columns(2)
                    if d1.button("Yes, delete it", type="primary", key="%s_delok_%d" % (prefix, m["id"])):
                        db.delete_med(m["id"])
                        _clear(prefix + "_del")
                        _flash("info", "Deleted %s." % m["name"])
                        st.rerun()
                    d2.button("Keep it", key="%s_delno_%d" % (prefix, m["id"]), on_click=_clear, args=(prefix + "_del",))


def render(ctx):
    st.markdown(ui.hero("My Medicines", "Add each medicine exactly as your healthcare professional told you. "
                        "Pilly will remind you at the times you choose.", "tips", eyebrow="Schedule", height=210), unsafe_allow_html=True)
    med_manager(ctx, "med")
    st.markdown(ui.tip_box("<b>Pilly's tip:</b> Use the details box for information from your prescription, such as "
                           "&ldquo;after food&rdquo;. These details show up on your dashboard and in every reminder."), unsafe_allow_html=True)
    st.markdown(ui.legal(), unsafe_allow_html=True)
'''),
('screens.onboarding', r'''"""First-time onboarding: Welcome -> Meet Pilly -> Medicines -> Review & confirm."""
import streamlit as st

from .. import db, logic as L, reminders, ui
from .medicines import med_manager

LABELS = ["Welcome", "Meet Pilly", "Medicines", "Review"]
ORDER = {"welcome": 0, "meet": 1, "intro": 1, "meds": 2, "review": 3}


def go(step):
    st.session_state["ob_step"] = step


PREFS = [("Automatic reminders", "reminders_enabled"), ("Show the Pilly pop-up when a dose is due", "popup"),
         ("Play a sound with reminders", "audio"), ("Show the 'due now' banner on the dashboard", "banner")]


def _save_pref(key):
    db.set_setting(key, "1" if st.session_state["ob_pref_" + key] else "0")


def _pref(label, key):
    st.toggle(label, value=db.get_settings()[key] == "1", key="ob_pref_" + key, on_change=_save_pref, args=(key,))


def confirm():
    db.save_profile(onboarded=True)
    st.session_state["ob_step"] = "welcome"
    st.session_state["page"] = "dashboard"
    st.session_state["flash"] = {"kind": "welcome", "text": "You're all set. Pilly will remind you while MedTimer is open."}


def render(ctx):
    st.markdown('<span class="onboarding-flag"></span>', unsafe_allow_html=True)
    step = st.session_state.setdefault("ob_step", "welcome")
    st.markdown(ui.steps(ORDER[step], LABELS), unsafe_allow_html=True)
    p = db.get_profile()

    if step == "welcome":
        st.markdown(ui.hero("Welcome to MedTimer", "Your daily medicine companion &mdash; calm, classic and always on time.",
                            "welcome", eyebrow="Hello there", height=300), unsafe_allow_html=True)
        _, mid, _ = st.columns([1, 2, 1])
        mid.button("Get started", type="primary", key="ob_start", on_click=go, args=("meet",))
        st.markdown(ui.legal(), unsafe_allow_html=True)

    elif step == "meet":
        c1, c2 = st.columns([1, 1.3], vertical_alignment="center")
        c1.markdown('<div style="text-align:center">%s</div>' % ui.pilly_img("welcome", 340), unsafe_allow_html=True)
        with c2:
            st.markdown(ui.bubble("Hi! I'm Pilly!!!", "Before we begin, what should I call you?"), unsafe_allow_html=True)
            with st.form("ob_profile"):
                name = st.text_input("Your preferred name", value=p["name"], max_chars=40, placeholder="e.g. Dhara")
                age = st.number_input("Your age (optional)", min_value=1, max_value=120, value=p["age"], step=1)
                ok = st.form_submit_button("Continue", type="primary")
            if ok:
                if not name.strip():
                    st.error("Please tell Pilly your name first.")
                else:
                    db.save_profile(name=name.strip(), age=int(age) if age else None)
                    go("intro")
                    st.rerun()
        st.button("Back", key="ob_back_meet", on_click=go, args=("welcome",))

    elif step == "intro":
        name = ui.esc(p["name"])
        c1, c2 = st.columns([1, 1.3], vertical_alignment="center")
        c1.markdown('<div style="text-align:center">%s</div>' % ui.pilly_img("welcome", 340), unsafe_allow_html=True)
        with c2:
            st.markdown(ui.bubble("Hi! I'm Pilly!!! Nice to meet you, %s!" % name,
                                  "I'm here to help you stay organised and keep track of your daily medicine routine. "
                                  "Let's get started!"), unsafe_allow_html=True)
            a, b = st.columns(2)
            a.button("Change my name", key="ob_edit_name", on_click=go, args=("meet",))
            b.button("Add my medicines", type="primary", key="ob_to_meds", on_click=go, args=("meds",))

    elif step == "meds":
        c1, c2 = st.columns([1, 3], vertical_alignment="center")
        c1.markdown('<div style="text-align:center">%s</div>' % ui.pilly_img("reminder", 190, "pilly-still"), unsafe_allow_html=True)
        c2.markdown('<h2 style="margin:0">Tell me about your medicines</h2><div class="muted">Add as many as you need. '
                    'Enter the name, time and days exactly as your healthcare professional advised.</div>', unsafe_allow_html=True)
        med_manager(ctx, "ob")
        with st.container(key="card_ob_snooze"):
            st.markdown('<div class="card-title">How long should a snooze last?</div><div class="muted">When a reminder pops up you can '
                        'snooze it. Choose a preset or type your own number of minutes. You can change this any time in Reminders.</div>',
                        unsafe_allow_html=True)
            reminders.snooze_picker(ctx, "ob_snz", persist=True)
        with st.container(key="card_ob_prefs"):
            st.markdown('<div class="card-title">Reminder preferences</div><div class="muted">Choose how Pilly should remind you. '
                        'You can change these any time in Reminders.</div>', unsafe_allow_html=True)
            for label, key in PREFS:
                _pref(label, key)
        n = len(db.list_meds())
        a, b = st.columns(2)
        a.button("Back", key="ob_back_meds", on_click=go, args=("intro",))
        b.button("Review and confirm", type="primary", key="ob_to_review", on_click=go, args=("review",), disabled=(n == 0))
        if n == 0:
            st.caption("Add at least one medicine to continue.")

    elif step == "review":
        meds = db.list_meds()
        c1, c2 = st.columns([1, 1.6], vertical_alignment="top")
        c1.markdown('<div style="text-align:center">%s</div>' % ui.pilly_img("completed", 300), unsafe_allow_html=True)
        with c2:
            with st.container(key="card_review"):
                st.markdown('<div class="card-title">Please check your details</div>', unsafe_allow_html=True)
                st.markdown("**Name:** %s &nbsp;&nbsp; **Age:** %s &nbsp;&nbsp; **Snooze:** %d min"
                            % (ui.esc(p["name"]), p["age"] if p["age"] else "not given", ctx.snooze), unsafe_allow_html=True)
                st.markdown("**Reminders:** " + " &middot; ".join("%s %s" % (lab, "on" if ctx.on(k) else "off") for lab, k in
                            (("Automatic", "reminders_enabled"), ("Pop-up", "popup"), ("Sound", "audio"), ("Banner", "banner"))),
                            unsafe_allow_html=True)
                st.markdown('<hr class="gold-rule"/>', unsafe_allow_html=True)
                for m in meds:
                    st.markdown('<div class="dose" style="margin-bottom:.45rem"><span class="nm">%s</span>'
                                '<span class="tm">%s &middot; %s</span>%s</div>'
                                % (ui.esc(m["name"]), L.fmt_time(m["time"], ctx.h24), L.fmt_days(m["days"]),
                                   '<span class="nt">%s</span>' % ui.esc(m["notes"]) if m["notes"] else ""), unsafe_allow_html=True)
                if not meds:
                    st.warning("No medicines added yet.")
        a, b, c = st.columns(3)
        a.button("Edit my details", key="ob_edit_info", on_click=go, args=("meet",))
        b.button("Edit medicines", key="ob_edit_meds", on_click=go, args=("meds",))
        c.button("Confirm and continue", type="primary", key="ob_confirm", on_click=confirm, disabled=(not meds))
        st.markdown(ui.legal(), unsafe_allow_html=True)
'''),
('screens.dashboard', r'''"""Dashboard: greeting, adherence ring, status counts, next reminder and today's checklist."""
import streamlit as st

from .. import logic as L, reminders, ui


def render(ctx):
    today, now = ctx.today, ctx.now
    doses = L.doses_for_day(ctx.meds, today)
    s = L.day_stats(ctx.meds, today, now, ctx.log, ctx.window, ctx.rstate)
    done = s["total"] > 0 and s["taken"] == s["total"]
    sub = today.strftime("%A, %d %B %Y")
    st.markdown(ui.hero("%s, %s!" % (L.greeting(now), ui.esc(ctx.name)), sub, "completed" if done else "welcome",
                        eyebrow="Today", height=220), unsafe_allow_html=True)

    # ---- due-now banner (yellow) -------------------------------------------------
    due_now = [m for m in doses if L.is_due_now(m, today, now, ctx.log, ctx.window, ctx.rstate)]
    if due_now and ctx.on("banner"):
        names = ", ".join("<b>%s</b> (%s)" % (ui.esc(m["name"]), L.fmt_time(m["time"], ctx.h24)) for m in due_now)
        st.markdown('<div class="banner due"><span class="ico-wrap">%s</span><span>Time to check: %s. Tick it off in the list below, or let Pilly remind you again.</span></div>'
                    % (ui.icon("clock"), names), unsafe_allow_html=True)

    # ---- numbers --------------------------------------------------------------------
    if s["total"] == 0:
        ring_note = "No doses are scheduled today."
    elif s["due"]:
        ring_note = "%d of %d due dose%s taken" % (s["taken"], s["due"], "" if s["due"] == 1 else "s")
        if s["upcoming"]:
            ring_note += " &middot; %d still to come" % s["upcoming"]
    else:
        ring_note = "Nothing is due yet &middot; %d dose%s to come today" % (s["upcoming"], "" if s["upcoming"] == 1 else "s")
    c1, c2 = st.columns([1, 2.2], vertical_alignment="center")
    with c1:
        with st.container(key="card_ring"):
            st.markdown('<div class="ring">%s<div><div class="card-title" style="margin:0">Daily adherence</div>'
                        '<div class="muted small">%s</div></div></div>' % (ui.ring(s["pct"]), ring_note),
                        unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="grid">%s%s%s%s</div>' % (
            ui.stat(s["total"], "Scheduled today", "n0", "bell"), ui.stat(s["taken"], "Taken", "g", "check"),
            ui.stat(s["upcoming"], "Upcoming", "y", "clock"), ui.stat(s["missed"], "Missed", "r", "cross")), unsafe_allow_html=True)

    # ---- next reminder + Pilly's message --------------------------------------------
    nxt = L.next_reminder(ctx.meds, now, ctx.log, ctx.rstate, ctx.window) if ctx.on("reminders_enabled") else None
    if not ctx.on("reminders_enabled"):
        nxt_html = "Reminders are switched off. You can turn them on in Settings."
    elif nxt:
        kind = "Snoozed reminder" if nxt["kind"] == "snoozed" else "Next reminder"
        nxt_html = "<b>%s:</b> %s &middot; %s" % (kind, ui.esc(nxt["med"]["name"]), L.fmt_when(nxt["when"], now, ctx.h24))
    else:
        nxt_html = "No upcoming reminders. Add a medicine to get started."
    m1, m2 = st.columns([1, 1])
    m1.markdown(ui.note("bell", nxt_html), unsafe_allow_html=True)
    m2.markdown(ui.note("spark", ui.esc(L.pilly_message(s, ctx.name)), "background:#fff"), unsafe_allow_html=True)

    # ---- checklist -------------------------------------------------------------------
    st.markdown('<h3 style="margin:1rem 0 .4rem">Today\'s checklist</h3>', unsafe_allow_html=True)
    if not doses:
        st.info("Nothing is scheduled for today. Enjoy a calm day!")
    for m in doses:
        stt = L.status_of(m, today, now, ctx.log, ctx.window, ctx.rstate)
        at = ctx.log.get((today.isoformat(), m["id"]))
        until = L.snoozed_until(ctx.rstate.get(m["id"]), now)
        extra = ('<span class="muted small">taken at %s</span>' % L.fmt_time(at, ctx.h24) if at else
                 '<span class="muted small">snoozed until %s</span>' % L.fmt_time(until.strftime("%H:%M"), ctx.h24) if until else "")
        note = '<span class="nt">%s</span>' % ui.esc(m["notes"]) if m["notes"] else ""
        with st.container(key="card_dose_%s_%d" % (stt, m["id"])):
            a, b = st.columns([3, 1.4], vertical_alignment="center")
            a.markdown('<div class="dose">%s<span class="nm">%s</span><span class="tm">%s</span>%s%s</div>'
                       % (ui.pill(stt), ui.esc(m["name"]), L.fmt_time(m["time"], ctx.h24), extra, note), unsafe_allow_html=True)
            if stt == "taken":
                b.button("Undo", key="undo_%d" % m["id"], on_click=reminders.undo_dose, args=(m["id"],))
            else:
                b.button("Mark as Taken", type="primary", key="take_%d" % m["id"], on_click=reminders.take_dose, args=(m["id"], "checklist"))
    st.markdown(ui.legal(), unsafe_allow_html=True)
'''),
('screens.progress', r'''"""Weekly progress: seven-day chart, per-day percentages and totals (shown inside the History tab)."""
import streamlit as st

from .. import logic as L, ui


def body(ctx):
    df = L.week_frame(ctx.meds, ctx.today, ctx.now, ctx.log, ctx.window, state=ctx.rstate)
    sm = L.week_summary(df)
    if sm["pct"] is None:
        text = "Your week will fill in as doses come due."
    elif sm["pct"] >= 90:
        text = "A wonderful week so far, %s. Beautiful consistency!" % ui.esc(ctx.name)
    else:
        text = "Every check-in counts, %s. Here's how your week looks." % ui.esc(ctx.name)
    st.markdown(ui.note("spark", text, "background:#fff"), unsafe_allow_html=True)

    st.markdown('<div class="grid">%s%s%s%s</div>' % (
        ui.stat(sm["scheduled"], "Scheduled this week", "n0"), ui.stat(sm["taken"], "Taken", "g", "check"),
        ui.stat(sm["missed"], "Missed", "r", "cross"),
        ui.stat("&ndash;" if sm["pct"] is None else "%d%%" % round(sm["pct"]), "Weekly adherence", "gold")), unsafe_allow_html=True)

    with st.container(key="card_chart"):
        st.markdown('<div class="card-title">Daily adherence &middot; %s &ndash; %s</div><div class="muted small">Each bar shows doses '
                    'taken out of doses that have come due. Hatched bars mean nothing was due that day.</div>'
                    % (df["date"].iloc[0].strftime("%d %b"), df["date"].iloc[-1].strftime("%d %b")), unsafe_allow_html=True)
        st.markdown(ui.bar_chart(df, ctx.today), unsafe_allow_html=True)

    with st.expander("See the numbers"):
        show = df.assign(Date=df["date"].map(lambda d: d.strftime("%a %d %b")),
                         Adherence=df["adherence"].map(lambda v: "-" if v is None or v != v else "%d%%" % round(v)))[
            ["Date", "scheduled", "taken", "missed", "upcoming", "Adherence"]]
        show.columns = ["Date", "Scheduled", "Taken", "Missed", "Still to come", "Adherence"]
        st.dataframe(show, hide_index=True)
        st.caption("Weekly adherence = taken / (taken + missed). Doses still to come are not counted against you.")
'''),
('screens.reports', r'''"""Reports: downloadable daily / weekly / schedule files (CSV + text) and the reminder history (shown inside History)."""
import streamlit as st

from .. import db, reports as R


def _card(key, title, blurb, df, ctx, csv_name, txt_title, footer=None):
    with st.container(key="card_rep_" + key):
        st.markdown('<div class="card-title">%s</div><div class="muted small" style="margin-bottom:.5rem">%s</div>' % (title, blurb),
                    unsafe_allow_html=True)
        with st.expander("Preview"):
            st.dataframe(df, hide_index=True)
        a, b = st.columns(2)
        a.download_button("Download CSV", R.to_csv(df), file_name=csv_name + ".csv", mime="text/csv", key="dl_csv_" + key)
        b.download_button("Download text", R.to_text(txt_title, ctx.profile, ctx.now, df, footer), file_name=csv_name + ".txt",
                          mime="text/plain", key="dl_txt_" + key)


def body(ctx):
    stamp = ctx.today.isoformat()
    daily = R.daily_df(ctx.meds, ctx.today, ctx.now, ctx.log, ctx.window, ctx.h24, ctx.rstate)
    weekly, sm = R.weekly_df(ctx.meds, ctx.today, ctx.now, ctx.log, ctx.window, ctx.rstate)
    sched = R.schedule_df(ctx.meds, ctx.h24)
    foot = ["Total scheduled: %d   Taken: %d   Missed: %d   Adherence: %s" % (
        sm["scheduled"], sm["taken"], sm["missed"], "-" if sm["pct"] is None else "%d%%" % round(sm["pct"]))]
    _card("daily", "Daily report", "Today's doses and whether each was taken.", daily, ctx, "MedTimer_Daily_" + stamp, "Daily Report")
    _card("weekly", "Weekly report", "Monday to Sunday, with adherence for each day.", weekly, ctx, "MedTimer_Weekly_" + stamp,
          "Weekly Report", foot)
    _card("schedule", "Medicine schedule", "Everything you've asked MedTimer to remind you about.", sched, ctx,
          "MedTimer_Schedule_" + stamp, "Medicine Schedule")

    with st.container(key="card_rep_history"):
        st.markdown('<div class="card-title">Reminder history</div><div class="muted small">The latest reminders, snoozes and check-ins.</div>',
                    unsafe_allow_html=True)
        hist = R.history_df(db.list_events(100))
        if hist.empty:
            st.caption("No reminders yet. They'll appear here as they happen.")
        else:
            st.dataframe(hist, hide_index=True)
            st.download_button("Download history (CSV)", R.to_csv(hist), file_name="MedTimer_ReminderHistory_%s.csv" % stamp,
                               mime="text/csv", key="dl_hist")
'''),
('screens.achievements', r'''"""Achievements: four badges, streak, and the Turtle-graphics medal."""
import os

import streamlit as st

from .. import db, logic as L, turtle_badge, ui

ICONS = {"first_day": "moon", "consistency": "spark", "weekly_star": "star", "routine_builder": "leaf"}


def _badge_uri(count, total, name):
    path = turtle_badge.badge_path(count, total, name)
    if not os.path.exists(path):          # drawn once with Turtle, then reused from disk
        turtle_badge.render_badge(path, count, total, name)
    return ui.file_uri(path)


def render(ctx):
    got = db.get_achievements()
    n = len(got)
    text = ("You've unlocked <b>%d of %d</b> achievements, %s." % (n, len(L.ACHIEVEMENTS), ui.esc(ctx.name)) if n
            else "Take your doses and Pilly will celebrate every milestone with you.")
    st.markdown(ui.hero("Achievements", text, "achievement" if n else "welcome", eyebrow="Milestones", height=250,
                        cls="pilly-float"), unsafe_allow_html=True)
    c1, c2 = st.columns([1.5, 1], vertical_alignment="top")
    with c1:
        for key, (title, desc, _msg) in L.ACHIEVEMENTS.items():
            have = key in got
            when = got[key]["at"][:10] if have else ""
            with st.container(key="card_ach_" + key):
                st.markdown('<div class="ach %s"><div class="ico">%s</div><div><div class="t">%s</div>'
                            '<div class="muted small">%s</div>%s</div></div>'
                            % ("" if have else "locked", ui.icon(ICONS[key]), title, desc,
                               '<div class="small" style="color:#33612F;font-weight:700">%s Unlocked %s</div>' % (ui.icon("check"), when) if have
                               else '<div class="small muted">Locked</div>'), unsafe_allow_html=True)
    with c2:
        with st.container(key="card_medal"):
            st.markdown('<div class="card-title">Your medal</div><div style="text-align:center"><img src="%s" alt="Achievement medal" '
                        'style="max-width:100%%;width:340px;border-radius:14px"/></div>'
                        '<div class="muted small" style="text-align:center;margin-top:.4rem">Drawn with Python Turtle graphics.</div>'
                        % _badge_uri(n, len(L.ACHIEVEMENTS), ctx.name), unsafe_allow_html=True)
    st.markdown(ui.legal(), unsafe_allow_html=True)
'''),
('screens.history', r'''"""History tab: what was taken or missed day by day, weekly progress and downloadable reports."""
import streamlit as st

from .. import logic as L, reports as R, ui
from . import progress, reports as report_screen

RANGES = {"Last 7 days": 7, "Last 14 days": 14, "Last 30 days": 30}
FILTERS = ["All", "Taken", "Missed"]


def _day_card(d, rows, ctx):
    body = "".join(
        '<div class="dose" style="margin:.45rem 0">%s<span class="nm">%s</span><span class="tm">%s</span>%s</div>'
        % (ui.pill(r["status"]), ui.esc(r["med"]), L.fmt_time(r["time"], ctx.h24),
           '<span class="muted small">taken at %s</span>' % L.fmt_time(r["taken_at"], ctx.h24) if r["taken_at"] else "")
        for r in rows)
    title = "Today" if d == ctx.today else d.strftime("%A, %d %B")
    with st.container(key="card_hist_" + d.isoformat()):
        st.markdown('<div class="card-title">%s</div>%s' % (title, body), unsafe_allow_html=True)


def _log(ctx):
    c1, c2 = st.columns(2)
    label = c1.selectbox("Show", list(RANGES), key="hist_range")
    which = c2.selectbox("Status", FILTERS, key="hist_filter")
    full = L.dose_history(ctx.meds, ctx.today, ctx.now, ctx.log, ctx.window, RANGES[label], ctx.rstate)
    taken = sum(r["status"] == "taken" for _d, rows in full for r in rows)
    missed = sum(r["status"] == "missed" for _d, rows in full for r in rows)
    pct = "&ndash;" if not (taken + missed) else "%d%%" % round(100.0 * taken / (taken + missed))
    st.markdown('<div class="grid">%s%s%s</div>' % (ui.stat(taken, "Taken", "g", "check"), ui.stat(missed, "Missed", "r", "cross"),
                                                    ui.stat(pct, "Adherence", "gold")), unsafe_allow_html=True)
    shown = full
    if which != "All":
        shown = [(d, [r for r in rows if r["status"] == which.lower()]) for d, rows in full]
        shown = [(d, rows) for d, rows in shown if rows]
    if not shown:
        st.info("Nothing to show for this choice yet. Doses appear here once they are scheduled.")
        return
    for d, rows in shown:
        _day_card(d, rows, ctx)
    st.download_button("Download this list (CSV)", R.to_csv(R.log_df(shown, ctx.h24)),
                       file_name="MedTimer_DoseLog_%s.csv" % ctx.today.isoformat(), mime="text/csv", key="dl_doselog")


def render(ctx):
    st.markdown(ui.hero("History", "Look back at what you took, what you missed and how your week is going.",
                        "progress", eyebrow="Look back", height=210), unsafe_allow_html=True)
    tabs = st.tabs(["Taken & missed", "Weekly progress", "Reports"])
    with tabs[0]:
        _log(ctx)
    with tabs[1]:
        progress.body(ctx)
    with tabs[2]:
        report_screen.body(ctx)
    st.markdown(ui.legal(), unsafe_allow_html=True)
'''),
('screens.reminder_center', r'''"""Reminders tab: today's reminder state for every medicine, the snooze length, sound and pop-up options."""
import streamlit as st

from .. import audio, config as C, db, logic as L, reminders, ui


def _bool(v):
    return "1" if v else "0"


def _save(key, wkey, cast=str):
    db.set_setting(key, cast(st.session_state[wkey]))


def _toggle(ctx, label, key, help_=None):
    st.toggle(label, value=ctx.on(key), key="set_" + key, on_change=_save, args=(key, "set_" + key, _bool), help=help_)


def _goto(page):
    st.session_state["page"] = page


def _today_chip(ctx, m):
    """Where today's reminder for this medicine stands."""
    day, now = ctx.today, ctx.now
    if day.weekday() not in m["days"] or day.isoformat() < m["created"]:
        return '<span class="muted">No reminder today</span>'
    if (day.isoformat(), m["id"]) in ctx.log:
        return '<span class="pill taken">%s Taken at %s</span>' % (ui.icon("check"), L.fmt_time(ctx.log[(day.isoformat(), m["id"])], ctx.h24))
    until = L.snoozed_until(ctx.rstate.get(m["id"]), now)
    if until:
        return '<span class="pill upcoming">%s Snoozed until %s</span>' % (ui.icon("clock"), L.fmt_time(until.strftime("%H:%M"), ctx.h24))
    if L.status_of(m, day, now, ctx.log, ctx.window, ctx.rstate) == "missed":
        return '<span class="pill missed">%s Missed</span>' % ui.icon("cross")
    if L.due_at(m, day) > now:
        return '<span class="pill upcoming">%s Reminds at %s</span>' % (ui.icon("clock"), L.fmt_time(m["time"], ctx.h24))
    return '<span class="pill upcoming">%s Reminder due</span>' % ui.icon("clock")


def _schedule(ctx):
    if not ctx.meds:
        st.info("No medicines yet. Add one in My Medicines and its reminder will appear here.")
    for m in ctx.meds:
        today_ok = ctx.today.weekday() in m["days"] and ctx.today.isoformat() >= m["created"]
        stt = L.status_of(m, ctx.today, ctx.now, ctx.log, ctx.window, ctx.rstate) if today_ok else "none"
        with st.container(key="card_rem_%s_%d" % (stt, m["id"])):
            a, b = st.columns([3, 2], vertical_alignment="center")
            a.markdown('<div class="dose"><span class="nm">%s</span><span class="tm">%s &middot; %s</span></div>'
                       % (ui.esc(m["name"]), L.fmt_time(m["time"], ctx.h24), L.fmt_days(m["days"])), unsafe_allow_html=True)
            b.markdown(_today_chip(ctx, m), unsafe_allow_html=True)
    st.button("Change times in My Medicines", key="rem_goto_meds", on_click=_goto, args=("medicines",))


def _snooze(ctx):
    with st.container(key="card_snooze"):
        st.markdown('<div class="card-title">How long should a snooze last?</div><div class="muted">Pick a preset or type your own '
                    'number of minutes. Your choice is saved and used by the Snooze button on every reminder.</div>',
                    unsafe_allow_html=True)
        minutes = reminders.snooze_picker(ctx, "rem_snz", persist=True)
        st.markdown(ui.note("bell", "Saved: snooze lasts <b>%d minutes</b>. If you snoozed right now, Pilly would remind you "
                            "again at <b>%s</b>." % (minutes, reminders.remind_at(ctx, minutes))), unsafe_allow_html=True)


def _alerts(ctx):
    with st.container(key="card_alerts"):
        _toggle(ctx, "Automatic reminders", "reminders_enabled", "Turn off to stop all pop-ups and reminder sounds.")
        _toggle(ctx, "Show the Pilly pop-up when a dose is due", "popup")
        _toggle(ctx, "Show the 'due now' banner on the dashboard", "banner")
        w = int(ctx.settings["window"])
        st.selectbox("Show a dose as missed after", C.WINDOW_CHOICES, index=C.WINDOW_CHOICES.index(w) if w in C.WINDOW_CHOICES else 3,
                     format_func=lambda m: "%d minutes" % m, key="set_window", on_change=_save, args=("window", "set_window"),
                     help="Also the longest a reminder may appear after its scheduled time.")
    with st.container(key="card_sound"):
        _toggle(ctx, "Play a sound with reminders", "audio")
        keys = list(C.SOUNDS)
        st.selectbox("Sound", keys, index=keys.index(ctx.settings["sound"]) if ctx.settings["sound"] in keys else 0,
                     format_func=lambda k: C.SOUNDS[k], key="set_sound", on_change=_save, args=("sound", "set_sound"))
        st.slider("Volume", 0, 100, int(ctx.settings["volume"]), key="set_volume", on_change=_save, args=("volume", "set_volume"))
        if st.button("Play a test sound", key="set_test_sound"):
            reminders.play_hidden(ctx.settings["sound"], ctx.settings["volume"])
        st.caption("Some browsers only allow sound after you've clicked something on the page. If you hear nothing, click the button again.")
    st.info("Reminders appear while MedTimer is open in a browser tab (the tab can be in the background). They cannot appear if the "
            "tab or browser is closed or the computer is asleep, and MedTimer does not send operating-system push notifications.")


def render(ctx):
    st.markdown(ui.hero("Reminders", "Choose when and how Pilly reminds you, and how long a snooze lasts.", "reminder",
                        eyebrow="Alerts", height=210), unsafe_allow_html=True)
    tabs = st.tabs(["Schedule", "Snooze", "Sound & alerts"])
    with tabs[0]:
        _schedule(ctx)
    with tabs[1]:
        _snooze(ctx)
    with tabs[2]:
        _alerts(ctx)
    st.markdown(ui.legal(), unsafe_allow_html=True)
'''),
('screens.settings', r'''"""Settings: profile, time zone and data management. (Medicines live in My Medicines; reminders, snooze and sound in Reminders.)"""
import functools
import json

import streamlit as st

from .. import config as C, db, ui


@functools.lru_cache(maxsize=1)
def _zones():
    try:
        from zoneinfo import available_timezones
        z = sorted(t for t in available_timezones() if "/" in t or t == "UTC")
    except Exception:
        z = []
    return z or ["Asia/Kolkata", "UTC"]


def _bool(v):
    return "1" if v else "0"


def _save_tz():
    db.save_profile(tz=st.session_state["set_tz"])


def _confirm(label, key, action, warning, primary=False):
    ss = st.session_state
    if ss.get(key):
        st.warning(warning)
        a, b = st.columns(2)
        if a.button("Yes, continue", type="primary", key=key + "_yes"):
            ss.pop(key, None)
            action()
            st.rerun()
        b.button("Cancel", key=key + "_no", on_click=lambda: ss.pop(key, None))
    else:
        st.button(label, key=key + "_ask", on_click=lambda: ss.__setitem__(key, True), type="primary" if primary else "secondary")


def _clear_today(ctx):
    db.clear_day_log(ctx.today)
    st.session_state["flash"] = {"kind": "info", "text": "Today's log was cleared."}


def _reset():
    db.reset_everything()
    st.session_state.clear()


def render(ctx):
    st.markdown(ui.hero("Settings", "Make MedTimer feel just right for you.", "tips", eyebrow="Preferences", height=190), unsafe_allow_html=True)
    tabs = st.tabs(["Profile", "Time zone", "Data"])

    with tabs[0]:
        with st.form("set_profile"):
            name = st.text_input("Preferred name", value=ctx.profile["name"], max_chars=40)
            age = st.number_input("Age (optional)", min_value=1, max_value=120, value=ctx.profile["age"], step=1)
            h24 = st.toggle("Show times in 24-hour format", value=ctx.h24)
            ok = st.form_submit_button("Save profile", type="primary")
        if ok:
            if not name.strip():
                st.error("Please enter a name.")
            else:
                db.save_profile(name=name.strip(), age=int(age) if age else None)
                db.set_setting("h24", _bool(h24))
                st.session_state["flash"] = {"kind": "info", "text": "Profile saved."}
                st.rerun()

    with tabs[1]:
        zones = _zones()
        cur = ctx.profile["tz"]
        st.selectbox("Your time zone", zones, index=zones.index(cur) if cur in zones else 0, key="set_tz", on_change=_save_tz)
        st.markdown("Local time now: **%s**" % ctx.now.strftime("%a %d %b %Y, %I:%M %p"))
        st.caption("Reminders follow this time zone, not your browser's.")

    with tabs[2]:
        st.markdown("MedTimer keeps your details only while the app is running. When the app is stopped and started again "
                    "you begin afresh with the set-up screens. Download a backup if you would like to keep a copy.")
        st.download_button("Download a backup (JSON)", json.dumps(db.export_all(), indent=2).encode("utf-8"),
                           file_name="MedTimer_backup_%s.json" % ctx.today.isoformat(), mime="application/json", key="dl_backup")
        st.markdown("&nbsp;", unsafe_allow_html=True)
        _confirm("Clear today's log", "set_clear_today", lambda: _clear_today(ctx), "Remove today's taken marks and reminder state?")
        _confirm("Clear reminder history", "set_clear_hist", db.clear_history, "Delete the reminder history list?")
        _confirm("Reset everything", "set_reset", _reset, "This deletes your profile, medicines, history and settings, and "
                 "restarts the welcome tour. It cannot be undone.", primary=True)
    st.markdown(ui.legal(), unsafe_allow_html=True)
'''),
]


def _load_modules():
    """Execute the embedded modules once per process (again only if their source changes), not on every rerun.
    Re-running them each time threw away the image/sound caches and made every click slower."""
    sig = hashlib.md5("".join(n + s for n, s in MODULES).encode("utf-8")).hexdigest()
    if getattr(sys.modules.get("medtimer"), "_sig", None) == sig:
        return
    pkg = types.ModuleType("medtimer"); pkg.__path__ = []; pkg.__file__ = os.path.join(HERE, "medtimer", "__init__.py")
    pkg._sig = None
    sys.modules["medtimer"] = pkg
    sub = types.ModuleType("medtimer.screens"); sub.__path__ = []; sub.__package__ = "medtimer.screens"
    sys.modules["medtimer.screens"] = sub; pkg.screens = sub
    for name, src in MODULES:
        full = "medtimer." + name
        fname = "<MedTimer:%s>" % name
        linecache.cache[fname] = (len(src), None, src.splitlines(True), fname)   # keeps inspect/tracebacks working
        mod = types.ModuleType(full); mod.__file__ = fname
        mod.__package__ = full.rpartition(".")[0]
        sys.modules[full] = mod
        (sub if name.startswith("screens.") else pkg).__dict__[name.split(".")[-1]] = mod
        exec(compile(src, fname, "exec"), mod.__dict__)
    C = sys.modules["medtimer.config"]          # assets/ now means the folder next to this file
    C.ROOT = HERE
    C.ASSET_DIR = os.path.join(HERE, "assets")
    C.PILLY_DIR = os.path.join(C.ASSET_DIR, "pilly")
    C.GEN_DIR = os.path.join(C.ASSET_DIR, "generated")
    pkg._sig = sig


# =====================================================================================================
#  ENTRY POINT
# =====================================================================================================
st.set_page_config(page_title="MedTimer - Your Daily Medicine Companion", page_icon="\U0001F48A",
                   layout="wide", initial_sidebar_state="collapsed")
_load_modules()


@st.cache_resource
def _fresh_data_home():
    """A brand-new, empty temporary folder for the database.

    st.cache_resource lives as long as the Streamlit server process: the folder is created once when the app is
    started and shared by every rerun, tab switch and browser reload, so the user's entries survive normal use.
    Stopping and restarting the app creates a different, empty folder, so onboarding always starts again and
    nothing from an earlier run (old database, JSON file ...) is ever loaded. The folder is deleted on exit."""
    home = tempfile.mkdtemp(prefix="medtimer_")
    atexit.register(shutil.rmtree, home, ignore_errors=True)
    return home


from medtimer import config as C, db, logic as L, reminders, state, ui  # noqa: E402
C.DATA_DIR = _fresh_data_home()
C.DB_PATH = os.path.join(C.DATA_DIR, "medtimer.db")
from medtimer.screens import (achievements, dashboard, history, medicines, onboarding,  # noqa: E402
                              reminder_center, settings)

# Top navigation tabs. History holds the taken/missed log, weekly progress and reports; Reminders holds the
# schedule, snooze length, sound and pop-up options.
NAV = [("dashboard", "Dashboard", ":material/home:"), ("medicines", "My Medicines", ":material/medication:"),
       ("reminders", "Reminders", ":material/notifications_active:"), ("history", "History", ":material/history:"),
       ("achievements", "Achievements", ":material/star:"), ("settings", "Settings", ":material/settings:")]
SCREENS = {"dashboard": dashboard.render, "medicines": medicines.render, "reminders": reminder_center.render,
           "history": history.render, "achievements": achievements.render, "settings": settings.render}


@st.cache_resource
def boot(db_path):
    """Create the empty database tables once per app process (db_path only keys the cache)."""
    db.init_db()
    return True


def go(page):
    st.session_state["page"] = page


def top_nav(ctx):
    """Header (title + live day streak) and tab bar. Switching is plain session state, so it never leaves this page."""
    cur = st.session_state.get("page")
    cur = cur if cur in SCREENS else "dashboard"
    n = L.streak(ctx.meds, ctx.today, ctx.now, ctx.log, ctx.window, ctx.rstate)
    st.markdown('<div class="topbar"><span class="brand">MedTimer</span><span class="sep">|</span>'
                '<span class="brand-sub">Your Daily Medicine Companion</span><span class="sep">|</span>'
                '<span class="streak" title="Days in a row with every due dose taken">\U0001F525 <span class="n">%d</span> Day Streak</span></div>' % n,
                unsafe_allow_html=True)
    with st.container(key="topnav"):
        for col, (key, label, icon) in zip(st.columns(len(NAV), gap="small"), NAV):
            col.button(label, key="nav_" + key, icon=icon, type="primary" if cur == key else "secondary",
                       on_click=go, args=(key,))


def show_flash(ctx):
    f = st.session_state.pop("flash", None)
    if not f:
        return
    k, text = f.get("kind"), f.get("text", "")
    if k == "taken":
        if ctx.on("audio"):
            reminders.play_hidden("taken", ctx.settings["volume"])      # its own "dose logged" sound
        st.markdown(ui.flash("taken", "<b>%s</b> &middot; %s" % (ui.esc(f.get("med", "")), ui.esc(text)),
                             "Great job! Medicine logged successfully!"), unsafe_allow_html=True)
    elif k == "snoozed":
        st.markdown(ui.flash("snoozed", ui.esc(text), "Reminder postponed"), unsafe_allow_html=True)
    elif k == "welcome":
        st.markdown(ui.flash("welcome", ui.esc(text), "Welcome aboard!"), unsafe_allow_html=True)
    else:
        st.toast(text)


def celebrate(ctx):
    """Unlock newly earned achievements and play Pilly's short celebration once."""
    if len(db.get_achievements()) < len(L.ACHIEVEMENTS):      # nothing left to earn once all four are unlocked
        for key in L.evaluate_achievements(ctx.meds, ctx.log, ctx.today, ctx.now, ctx.window, ctx.rstate):
            if db.unlock(key, ctx.now):
                st.session_state.setdefault("celebrate", []).append(key)
    for key in st.session_state.pop("celebrate", [])[:2]:
        st.markdown(ui.celebration(ctx.name, L.achievement_message(key, ctx.name)), unsafe_allow_html=True)
        db.mark_celebrated(key)
    # anything unlocked earlier but never shown is marked as seen so it can't re-trigger
    for key, v in db.get_achievements().items():
        if not v["celebrated"]:
            db.mark_celebrated(key)


def main():
    ss = st.session_state
    boot(C.DB_PATH)
    st.markdown(ui.css(), unsafe_allow_html=True)
    if not ss.pop("_from_poller", False):
        ss.pop("dialog_open", None)          # a user action means any earlier pop-up is gone
    ctx = state.load()

    if not ctx.profile["onboarded"]:
        onboarding.render(ctx)
        return

    top_nav(ctx)
    reminders.poller()

    queue = ss.get("popup_queue") or []
    if queue:
        med_id = queue.pop(0)
        if ctx.on("popup"):
            ss["dialog_open"] = ctx.now
            reminders.reminder_dialog(med_id, ctx.today.isoformat())
        else:
            queue.clear()
            if ctx.on("audio"):
                reminders.play_hidden(ctx.settings["sound"], ctx.settings["volume"])

    show_flash(ctx)
    celebrate(ctx)
    SCREENS.get(ss.get("page"), dashboard.render)(ctx)


main()
