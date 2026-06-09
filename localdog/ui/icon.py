from __future__ import annotations

import math

from PySide6.QtCore import QByteArray, QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtSvg import QSvgRenderer


def _draw_dog(painter: QPainter, size: int, *,
              bg: QColor | None = None, fg: QColor = QColor("#ECECEC")) -> None:
    painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)

    if bg is not None:
        grad = QLinearGradient(0, 0, 0, size)
        grad.setColorAt(0.0, bg.lighter(115))
        grad.setColorAt(1.0, bg)
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.NoPen)
        r = size * 0.22
        painter.drawRoundedRect(QRectF(0, 0, size, size), r, r)

    pen = QPen(fg)
    pen.setWidthF(size * 0.085)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)

    u = size / 32.0

    path = QPainterPath()
    path.moveTo(8 * u, 12 * u)
    path.lineTo(11 * u, 19 * u)
    path.cubicTo(11 * u, 24 * u, 14 * u, 26 * u, 16 * u, 26 * u)
    path.cubicTo(18 * u, 26 * u, 21 * u, 24 * u, 21 * u, 19 * u)
    path.lineTo(24 * u, 12 * u)
    path.lineTo(21 * u, 14 * u)
    path.cubicTo(20 * u, 9 * u, 12 * u, 9 * u, 11 * u, 14 * u)
    path.closeSubpath()
    painter.drawPath(path)

    painter.setBrush(QBrush(fg))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(QPoint(int(13.5 * u), int(18 * u)), int(0.85 * u), int(0.85 * u))
    painter.drawEllipse(QPoint(int(18.5 * u), int(18 * u)), int(0.85 * u), int(0.85 * u))


def make_icon(size: int = 256) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    _draw_dog(p, size, bg=QColor("#16181B"))
    p.end()
    return QIcon(pm)


def make_tray_icon(size: int = 64) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    _draw_dog(p, size, bg=None, fg=QColor("#ECECEC"))
    p.end()
    return QIcon(pm)


def _make_svg_icon(svg: str, size: int = 20, color: QColor = QColor("#ECECEC")) -> QIcon:
    svg_data = svg.format(color=color.name())
    renderer = QSvgRenderer(QByteArray(svg_data.encode("utf-8")))
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    renderer.render(painter)
    painter.end()
    return QIcon(pm)


def make_copy_icon(size: int = 18, color: QColor = QColor("#ECECEC")) -> QIcon:
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><rect x="9" y="9" width="12" height="12" rx="2" fill="{color}"/><path d="M7 5h9a2 2 0 0 1 2 2v9" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'''
    return _make_svg_icon(svg, size, color)


def make_refresh_icon(size: int = 18, color: QColor = QColor("#ECECEC")) -> QIcon:
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M4 4v6h6" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M20 20v-6h-6" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M5 14a7 7 0 0 1 12-5.5" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round"/><path d="M19 10.5a7 7 0 0 1-12 5.5" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round"/></svg>'''
    return _make_svg_icon(svg, size, color)


def make_play_icon(size: int = 18, color: QColor = QColor("#ECECEC")) -> QIcon:
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><polygon points="8,5 19,12 8,19" fill="{color}"/></svg>'''
    return _make_svg_icon(svg, size, color)


def make_stop_icon(size: int = 18, color: QColor = QColor("#ECECEC")) -> QIcon:
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="2" fill="{color}"/></svg>'''
    return _make_svg_icon(svg, size, color)


def make_test_icon(size: int = 18, color: QColor = QColor("#ECECEC")) -> QIcon:
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M6 12l5 5 7-11" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'''
    return _make_svg_icon(svg, size, color)


def make_gear_icon(size: int = 24, color: QColor = QColor("#ECECEC")) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(color)

    r_outer = size / 2 - 2
    painter.drawEllipse(QPointF(size / 2, size / 2), r_outer, r_outer)

    painter.setCompositionMode(QPainter.CompositionMode_Clear)
    r_inner = r_outer * 0.55
    painter.drawEllipse(QPointF(size / 2, size / 2), r_inner, r_inner)
    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

    painter.setBrush(color)
    tooth_w = size * 0.2
    tooth_h = size * 0.12
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        cx = size / 2 + (r_outer + 1) * 0.85 * math.cos(rad)
        cy = size / 2 + (r_outer + 1) * 0.85 * math.sin(rad)
        rect = QRectF(cx - tooth_w / 2, cy - tooth_h / 2, tooth_w, tooth_h)
        painter.drawEllipse(rect)

    painter.end()
    return QIcon(pm)


def make_update_icon(size: int = 20, color: QColor = QColor("#ECECEC")) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QPen(color, max(1, size / 8)))
    painter.setBrush(Qt.NoBrush)
    rect = QRectF(2, 2, size - 4, size - 4)
    painter.drawArc(rect, 0, 360 * 16)
    arrow_start = QPointF(size / 2, size / 4)
    arrow_mid = QPointF(size * 3 / 4, size / 2)
    arrow_end = QPointF(size / 2, size * 3 / 4)
    painter.drawLine(arrow_start, arrow_mid)
    painter.drawLine(arrow_mid, arrow_end)
    painter.end()
    return QIcon(pm)