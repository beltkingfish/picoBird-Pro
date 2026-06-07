"""
Central theme: display dimensions, layout constants, and color palette.

Colors are (r, g, b) tuples (0-255). The ILI9488 driver packs them to BGR666.
Both semantic names (C_*) and short legacy names (WHITE/BLACK/ACCENT/...) are
provided so every screen can import from one place.
"""

# ── Display geometry ─────────────────────────────────────────────────────────
WIDTH   = 320
HEIGHT  = 320

# ── Layout ───────────────────────────────────────────────────────────────────
LIST_Y    = 36    # first list row Y for full-screen lists
LIST_ROW_H = 12   # height of a list row
MENU_ROW_H = 20   # height of a menu row
FOOTER_Y  = 306   # footer hint line Y
LIST_VISIBLE = 21 # rows that fit below a list header

# ── Palette (semantic) ───────────────────────────────────────────────────────
C_BG      = (0, 0, 0)
C_FG      = (255, 255, 255)
C_HEADER  = (80, 200, 120)
C_DIM     = (100, 100, 100)
C_SEL     = (120, 255, 160)
C_SEL_FG  = (120, 255, 160)
C_SEL_BG  = (30, 90, 50)
C_ERR     = (255, 80, 80)
C_WARN    = (255, 160, 0)
C_OK      = (80, 255, 80)
C_CURSOR  = (255, 255, 0)
C_LABEL   = (140, 200, 255)
C_RECENT  = (160, 220, 255)
C_EMPTY   = (140, 140, 140)
C_QUICKLOG = (255, 220, 80)

# ── Legacy short names (used by sound.py and any future screens) ─────────────
BLACK   = C_BG
WHITE   = C_FG
ACCENT  = C_HEADER
GRAY    = C_DIM
GREEN   = C_OK
RED     = C_ERR
YELLOW  = C_CURSOR
