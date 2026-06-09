from __future__ import annotations

import sys

DARK_COLORS = {
    "bg":          "#0E0F11",
    "bg_elev":     "#16181B",
    "bg_input":    "#101215",
    "border":      "#26292E",
    "border_soft": "#1B1D21",
    "text":        "#ECECEC",
    "text_dim":    "#8A8F95",
    "text_faint":  "#5C6068",
    "accent":      "#7FB3FF",
    "ok":          "#5BD49B",
    "warn":        "#F0B86E",
    "err":         "#F07A7A",
}

LIGHT_COLORS = {
    "bg":          "#F2F3F5",
    "bg_elev":     "#FFFFFF",
    "bg_input":    "#F8F9FA",
    "border":      "#DDE0E4",
    "border_soft": "#E9ECEF",
    "text":        "#1A1D21",
    "text_dim":    "#4B5563",
    "text_faint":  "#9CA3AF",
    "accent":      "#0066FF",
    "ok":          "#10B981",
    "warn":        "#F59E0B",
    "err":         "#EF4444",
}

FONT_FAMILY = '"Figtree", -apple-system, "Segoe UI", Inter, Roboto, "Helvetica Neue", Arial, sans-serif'
MONO_FAMILY = '"JetBrains Mono", "SF Mono", Menlo, Consolas, monospace'

_current_theme = "dark"
_colors = DARK_COLORS
COLORS = _colors


def is_windows_dark_theme() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return value == 0
    except Exception:
        return False


def set_theme(theme: str) -> None:
    global _current_theme, _colors, COLORS
    if theme == "system" and sys.platform == "win32":
        _current_theme = "dark" if is_windows_dark_theme() else "light"
    elif theme in ("dark", "light"):
        _current_theme = theme
    else:
        _current_theme = "dark"
    _colors = DARK_COLORS if _current_theme == "dark" else LIGHT_COLORS
    COLORS = _colors


def stylesheet() -> str:
    c = _colors
    is_dark = _current_theme == "dark"
    btn_bg = "rgba(255, 255, 255, 0.04)" if is_dark else "rgba(0, 0, 0, 0.05)"
    
    return f"""
* {{
    font-family: {FONT_FAMILY};
    color: {c['text']};
    font-size: 13px;
}}

QWidget#root {{
    background: {c['bg'] if not is_dark else f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {c['bg']}, stop:1 {c['bg_elev']})"};
}}

QFrame#card {{
    background: {c['bg_elev']};
    border: 1px solid {c['border_soft']};
    border-radius: 20px;
    padding: 16px;
}}

QWidget#settings_container {{
    background: {c['bg']};
    border: 1px solid {c['border']};
    border-radius: 24px;
}}

QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

QFrame#hr {{
    background: {c['border_soft']};
    max-height: 1px;
    min-height: 1px;
    border: none;
}}

QLabel#h1 {{
    font-size: 26px;
    font-weight: 700;
    letter-spacing: -0.5px;
}}

QLabel#h2 {{
    font-size: 14px;
    font-weight: 700;
    color: {c['text_dim']};
    letter-spacing: 0.8px;
    text-transform: uppercase;
}}

QLabel#muted {{ color: {c['text_dim']}; }}
QLabel#faint {{ color: {c['text_faint']}; font-size: 11px; }}

QLabel#status {{
    font-size: 13px;
    font-weight: 500;
    padding: 4px 10px;
    border-radius: 9px;
    background: {c['border_soft']};
    color: {c['text_dim']};
}}
QLabel#status[state="on"] {{
    background: {"rgba(91, 212, 155, 0.12)" if is_dark else "rgba(46, 139, 87, 0.1)"};
    color: {c['ok']};
}}
QLabel#status[state="off"] {{
    background: {c['border_soft']};
    color: {c['text_dim']};
}}
QLabel#status[state="err"] {{
    background: {"rgba(240, 122, 122, 0.14)" if is_dark else "rgba(211, 47, 47, 0.1)"};
    color: {c['err']};
}}

QLabel#stat_value {{
    font-family: {MONO_FAMILY};
    font-size: 18px;
    font-weight: 500;
}}
QLabel#stat_label {{
    color: {c['text_faint']};
    font-size: 11px;
    letter-spacing: 0.6px;
    text-transform: uppercase;
}}

QLineEdit, QSpinBox, QPlainTextEdit, QComboBox {{
    background: {c['bg_input']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    padding: 8px 10px;
    selection-background-color: {c['accent']};
    selection-color: {c['bg']};
}}
QLineEdit:focus, QSpinBox:focus, QPlainTextEdit:focus, QComboBox:focus {{
    border-color: {c['accent']};
}}
QPlainTextEdit {{
    font-family: {MONO_FAMILY};
    font-size: 12px;
}}

QComboBox::drop-down {{
    border: none;
    width: 0px;
}}
QComboBox::down-arrow {{
    image: none;
    width: 0px;
    height: 0px;
}}

QSpinBox::up-button, QSpinBox::down-button {{
    width: 0px;
    height: 0px;
    subcontrol-origin: border;
}}
QSpinBox::up-arrow, QSpinBox::down-arrow {{
    image: none;
    width: 0px;
    height: 0px;
}}

QPushButton {{
    background: {btn_bg};
    color: {c['text']};
    border: 1px solid {c['border']};
    border-radius: 10px;
    padding: 6px 12px;
    font-weight: 600;
    min-height: 32px;
}}
QPushButton:hover {{
    background: {c['bg_input']};
    border-color: {c['text_faint']};
}}
QPushButton:pressed {{
    background: {c['border_soft']};
}}

QPushButton#primary {{
    background: {c['accent']};
    color: {c['bg']};
    border-color: transparent;
}}
QPushButton#primary:hover {{
    background: {"rgba(127, 179, 255, 0.9)" if is_dark else "rgba(0, 102, 255, 0.9)"};
}}
QPushButton#primary:pressed {{
    background: {"rgba(127, 179, 255, 0.8)" if is_dark else "rgba(0, 102, 255, 0.8)"};
}}

QPushButton#danger {{ color: {c['err']}; border-color: rgba(240, 122, 122, 0.4); }}
QPushButton#danger:hover {{ border-color: {c['err']}; }}

QPushButton#ghost {{
    background: transparent;
    border: none;
    color: {c['accent']};
    font-size: 13px;
    font-weight: 500;
    padding: 6px 12px;
}}
QPushButton#ghost:hover {{
    background: {c['border_soft']};
    border-radius: 8px;
}}

QPushButton#link_btn {{
    background: {c['bg_input']};
    border: 1px dashed {c['border']};
    color: {c['accent']};
    text-align: left;
    padding: 10px 12px;
    font-family: {MONO_FAMILY};
    font-size: 12px;
}}
QPushButton#link_btn:hover {{ border-style: solid; border-color: {c['accent']}; }}

QCheckBox {{ color: {c['text']}; spacing: 8px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {c['border']};
    border-radius: 4px;
    background: {c['bg_input']};
}}
QCheckBox::indicator:checked {{
    background: {c['accent']};
    border-color: {c['accent']};
    image: none;
}}

QTabWidget::pane {{
    border: none;
    background: transparent;
}}
QTabBar::tab {{
    background: transparent;
    color: {c['text_dim']};
    padding: 8px 16px;
    margin-right: 4px;
    border-radius: 0;
    font-weight: 500;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:hover {{
    color: {c['text']};
    border-bottom-color: {c['text_faint']};
}}
QTabBar::tab:selected {{
    color: {c['accent']};
    border-bottom: 2px solid {c['accent']};
}}

QGroupBox {{
    background: {c['bg_elev']};
    border: 1px solid {c['border_soft']};
    border-radius: 12px;
    margin-top: 12px;
    padding-top: 12px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px 0 5px;
    color: {c['text_dim']};
}}
QGroupBox::indicator {{
    image: none;
    width: 0px;
    height: 0px;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 4px;
}}
QScrollBar::handle:vertical {{
    background: {c['border']};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {c['text_faint']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

QMenu {{
    background: {c['bg_elev']};
    border: 1px solid {c['border']};
    border-radius: 10px;
    padding: 6px;
}}
QMenu::item {{
    padding: 6px 18px 6px 14px;
    border-radius: 6px;
}}
QMenu::item:selected {{ background: {c['border_soft']}; }}
QMenu::separator {{
    height: 1px;
    background: {c['border_soft']};
    margin: 6px 4px;
}}

QToolTip {{
    background: {c['bg_elev']};
    color: {c['text']};
    border: 1px solid {c['border']};
    border-radius: 6px;
    padding: 6px 10px;
}}

QPushButton#power_btn {{
    background: {c['border_soft']};
    color: {c['text_dim']};
    border: 2px solid {c['border']};
    border-radius: 75px;
    min-width: 150px;
    max-width: 150px;
    min-height: 150px;
    max-height: 150px;
    width: 150px;
    height: 150px;
    font-size: 64px;
    font-weight: normal;
    padding: 0;
    margin: 0;
    outline: none;
}}
QPushButton#power_btn[state="on"] {{
    background: rgba(91, 212, 155, 0.2);
    color: {c['ok']};
}}
QPushButton#power_btn[state="err"] {{
    background: rgba(240, 122, 122, 0.2);
    color: {c['err']};
}}

QPushButton#gear_btn {{
    background: transparent;
    border: none;
    border-radius: 18px;
}}
QPushButton#gear_btn:hover {{
    background: {c['border_soft']};
}}

QPushButton#update_btn {{
    background: transparent;
    border: none;
    border-radius: 18px;
}}
QPushButton#update_btn:hover {{
    background: {c['border_soft']};
}}

QLabel#status_home {{
    font-size: 14px;
    font-weight: 500;
    color: {c['text_dim']};
    margin-top: 8px;
}}
QLabel#status_home[state="on"] {{
    color: {c['ok']};
}}
QLabel#status_home[state="err"] {{
    color: {c['err']};
}}

QPushButton#back_btn {{
    background: transparent;
    border: none;
    padding: 8px;
    border-radius: 8px;
}}
QPushButton#back_btn:hover {{
    background: {c['border_soft']};
}}

/* Modern Card Components */
QFrame#icon_card {{
    background: {c['bg_elev']};
    border: 1px solid {c['border_soft']};
    border-radius: 12px;
}}
QFrame#icon_card:hover {{
    border-color: {c['border']};
}}

QLabel#card_title {{
    font-size: 14px;
    font-weight: 600;
    color: {c['text']};
}}
QLabel#card_subtitle {{
    font-size: 12px;
    color: {c['text_dim']};
}}
QLabel#icon_card_title {{
    font-size: 13px;
    font-weight: 600;
    color: {c['text']};
}}
QLabel#icon_card_subtitle {{
    font-size: 11px;
    color: {c['text_dim']};
}}

/* Section Header */
QLabel#section_header {{
    font-size: 11px;
    font-weight: 700;
    color: {c['text_faint']};
    letter-spacing: 1px;
    text-transform: uppercase;
    padding-left: 4px;
}}

/* Settings Input Row */
QWidget#settings_row {{
    background: transparent;
}}
QLabel#settings_label {{
    font-size: 13px;
    color: {c['text']};
    font-weight: 500;
}}
QPushButton#copy_btn, QPushButton#regen_btn {{
    background: {c['bg_input']};
    border: 1px dashed {c['border']};
    color: {c['accent']};
    padding: 8px 16px;
    border-radius: 10px;
    font-weight: 500;
}}
QPushButton#copy_btn:hover, QPushButton#regen_btn:hover {{
    border-style: solid;
    border-color: {c['accent']};
    background: {c['bg_elev']};
}}

QPushButton#help_btn {{
    background: transparent;
    border: none;
    color: {c['text_faint']};
    font-size: 14px;
    font-weight: 700;
    min-width: 20px;
    max-width: 20px;
}}
QPushButton#help_btn:hover {{
    color: {c['accent']};
}}
"""