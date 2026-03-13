"""Design system — Deep Navy + Electric Teal theme."""

import tkinter.font as tkfont

# ──────────────────────────────────────────────────────────────
# Color Palette — Deep Navy + Electric Teal (Tailwind CSS)
# ──────────────────────────────────────────────────────────────
COLORS = {
    "bg_primary":    "#0a0e17",     # Main background
    "bg_secondary":  "#111827",     # Sidebar / card background
    "bg_elevated":   "#1a2332",     # Card / section background
    "bg_input":      "#1e293b",     # Input field background

    "accent":        "#06b6d4",     # Cyan-500
    "accent_hover":  "#22d3ee",     # Cyan-400
    "accent_muted":  "#0891b2",     # Cyan-600
    "accent_dim":    "#164e63",     # Cyan-900

    "success":       "#10b981",     # Emerald-500
    "warning":       "#f59e0b",     # Amber-500
    "error":         "#ef4444",     # Red-500

    "text_primary":  "#f1f5f9",     # Slate-100
    "text_secondary":"#94a3b8",     # Slate-400
    "text_muted":    "#475569",     # Slate-600

    "border":        "#1e293b",     # Slate-800
    "divider":       "#334155",     # Slate-700

    "sidebar_bg":    "#0f1520",     # Sidebar background
    "sidebar_hover": "#1a2332",     # Sidebar item hover
    "sidebar_active":"#164e63",     # Sidebar active item

    "button_primary":"#06b6d4",     # Primary button
    "button_hover":  "#22d3ee",     # Button hover
    "button_text":   "#0a0e17",     # Button text (dark on bright)
}

# ──────────────────────────────────────────────────────────────
# Typography
# ──────────────────────────────────────────────────────────────
FONT_CANDIDATES = ["Pretendard", "Noto Sans KR", "Malgun Gothic", "Segoe UI"]
MONO_CANDIDATES = ["JetBrains Mono", "Cascadia Code", "Consolas", "Courier New"]

FONT_SIZES = {
    "h1": 20,
    "h2": 16,
    "h3": 13,
    "body": 12,
    "small": 10,
    "mono": 11,
}


def _detect_font(candidates: list) -> str:
    """Find first available font from candidate list."""
    available = set(tkfont.families())
    for name in candidates:
        if name in available:
            return name
    return candidates[-1]


_cached_font = None
_cached_mono = None


def get_font_family() -> str:
    global _cached_font
    if _cached_font is None:
        _cached_font = _detect_font(FONT_CANDIDATES)
    return _cached_font


def get_mono_family() -> str:
    global _cached_mono
    if _cached_mono is None:
        _cached_mono = _detect_font(MONO_CANDIDATES)
    return _cached_mono


def font(size_key: str = "body", bold: bool = False) -> tuple:
    """Return (family, size, weight) tuple for CTk widgets."""
    family = get_font_family()
    size = FONT_SIZES.get(size_key, 12)
    weight = "bold" if bold else "normal"
    return (family, size, weight)


def mono_font(size_key: str = "mono") -> tuple:
    family = get_mono_family()
    size = FONT_SIZES.get(size_key, 11)
    return (family, size)


# ──────────────────────────────────────────────────────────────
# Spacing (8px grid)
# ──────────────────────────────────────────────────────────────
SP = {"xs": 4, "sm": 8, "md": 16, "lg": 24, "xl": 32}

# ──────────────────────────────────────────────────────────────
# Layout
# ──────────────────────────────────────────────────────────────
SIDEBAR_WIDTH = 56           # Icon-only sidebar
SIDEBAR_EXPANDED = 200       # Sidebar with text labels
WINDOW_MIN_W = 1200
WINDOW_MIN_H = 750
CORNER_RADIUS = 8

# ──────────────────────────────────────────────────────────────
# Step Indicator / Pipeline Colors
# ──────────────────────────────────────────────────────────────
STEP_COLORS = {
    "pending":  "#4a5568",     # Gray-600
    "active":   "#06b6d4",     # Cyan-500
    "done":     "#10b981",     # Emerald-500
    "error":    "#ef4444",     # Red-500
}

STEP_LABELS = ["Parse", "Transform", "Write", "Validate", "QC"]

# Stat card accent color list
STAT_ACCENTS = ["#06b6d4", "#8b5cf6", "#f59e0b", "#10b981"]

# Geometry diagram colors
GEOM_COLORS = {
    "vessel":   "#f1f5f9",     # White-ish
    "source":   "#f59e0b",     # Amber
    "receiver": "#06b6d4",     # Teal
    "cable":    "#475569",     # Slate-600
    "water":    "#0c4a6e",     # Sky-900
}
