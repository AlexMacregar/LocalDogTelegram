from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QPropertyAnimation, QEasingCurve, Property, QRect, QRectF, Signal, QObject
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QMouseEvent
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame, QVBoxLayout, QPushButton, QGraphicsOpacityEffect
from PySide6.QtWidgets import QCheckBox

from localdog.ui import theme


class AnimatedColor:
    """Helper for smooth color transitions."""
    def __init__(self, widget: QWidget, property_name: str = "color"):
        self.widget = widget
        self.property_name = property_name
        self._color = QColor()
    
    def setColor(self, color: QColor) -> None:
        self._color = color
        self.widget.setStyleSheet(f"{self.property_name}: {color.name()};")


class Toggle(QWidget):
    """Modern iOS-style toggle switch."""
    toggled = Signal(bool)
    
    def __init__(self, parent=None, width: int = 50, height: int = 28) -> None:
        super().__init__(parent)
        self.setFixedSize(width, height)
        self._checked = False
        self._thumb_pos = 3
        self._animation = None
        self.setCursor(Qt.PointingHandCursor)
        
    @Property(float)
    def thumbPosition(self) -> float:
        return self._thumb_pos
    
    @thumbPosition.setter
    def thumbPosition(self, pos: float) -> None:
        self._thumb_pos = pos
        self.update()
    
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background track
        track_color = QColor(theme.COLORS["accent"]) if self._checked else QColor(theme.COLORS["border"])
        track_color.setAlpha(60 if not self._checked else 255)
        
        painter.setBrush(track_color)
        painter.setPen(Qt.NoPen)
        
        # Draw rounded rect track
        from PySide6.QtCore import QRectF
        track_rect = QRectF(0, 0, self.width(), self.height())
        painter.drawRoundedRect(track_rect, self.height() / 2, self.height() / 2)
        
        # Thumb
        thumb_radius = (self.height() - 6) / 2
        thumb_x = self._thumb_pos + 3
        thumb_y = (self.height() - thumb_radius * 2) / 2
        
        thumb_color = QColor(theme.COLORS["bg"])
        painter.setBrush(thumb_color)
        painter.drawEllipse(thumb_x, thumb_y, thumb_radius * 2, thumb_radius * 2)
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        pass
    
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.toggle()
    
    def toggle(self) -> None:
        self.setChecked(not self._checked)
    
    def setChecked(self, checked: bool) -> None:
        if self._checked == checked:
            return
        self._checked = checked
        
        # Animate thumb position
        target_pos = self.width() - self.height() + 3 if checked else 3
        
        if self._animation and self._animation.state() == QPropertyAnimation.Running:
            self._animation.stop()
        
        self._animation = QPropertyAnimation(self, b"thumbPosition", self)
        self._animation.setDuration(200)
        self._animation.setStartValue(self._thumb_pos)
        self._animation.setEndValue(target_pos)
        self._animation.setEasingCurve(QEasingCurve.InOutQuad)
        self._animation.start()
        
        self.toggled.emit(checked)
    
    def isChecked(self) -> bool:
        return self._checked


class Card(QFrame):
    """Modern card widget with subtle styling."""
    def __init__(self, parent=None, icon: QWidget = None, title: str = "", subtitle: str = "") -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumHeight(56)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        
        if icon or title or subtitle:
            header_layout = QHBoxLayout()
            header_layout.setSpacing(12)
            
            if icon:
                icon_container = QWidget()
                icon_layout = QVBoxLayout(icon_container)
                icon_layout.setContentsMargins(0, 0, 0, 0)
                icon_layout.setAlignment(Qt.AlignCenter)
                icon_layout.addWidget(icon)
                header_layout.addWidget(icon_container)
            
            text_layout = QVBoxLayout()
            text_layout.setSpacing(2)
            
            if title:
                title_label = QLabel(title)
                title_label.setObjectName("card_title")
                text_layout.addWidget(title_label)
            
            if subtitle:
                subtitle_label = QLabel(subtitle)
                subtitle_label.setObjectName("card_subtitle")
                subtitle_label.setWordWrap(True)
                text_layout.addWidget(subtitle_label)
            
            header_layout.addLayout(text_layout, 1)
            layout.addLayout(header_layout)
    
    def setContent(self, widget: QWidget) -> None:
        self.layout().addWidget(widget)


class IconCard(QWidget):
    """Card with icon, title and content area."""
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("icon_card")
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(14)
        
        self.icon_widget = QWidget()
        self.icon_layout = QVBoxLayout(self.icon_widget)
        self.icon_layout.setContentsMargins(0, 0, 0, 0)
        self.icon_layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.icon_widget)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(2)
        layout.addWidget(self.content_layout, 1)
        
        self.action_widget = QWidget()
        self.action_layout = QHBoxLayout(self.action_widget)
        self.action_layout.setContentsMargins(0, 0, 0, 0)
        self.action_layout.setSpacing(8)
        layout.addWidget(self.action_widget)
    
    def setIcon(self, icon: QWidget) -> None:
        self.icon_layout.addWidget(icon)
    
    def addTitle(self, title: str) -> QLabel:
        label = QLabel(title)
        label.setObjectName("icon_card_title")
        self.content_layout.addWidget(label)
        return label
    
    def addSubtitle(self, subtitle: str) -> QLabel:
        label = QLabel(subtitle)
        label.setObjectName("icon_card_subtitle")
        label.setWordWrap(True)
        self.content_layout.addWidget(label)
        return label
    
    def addControl(self, widget: QWidget) -> None:
        self.content_layout.addWidget(widget)
    
    def addAction(self, widget: QWidget) -> None:
        self.action_layout.addWidget(widget)


class StatusIndicator(QWidget):
    """Animated status indicator dot."""
    def __init__(self, parent=None, size: int = 10) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._color = QColor(theme.COLORS["text_faint"])
        self._pulse_enabled = False
        
    def setColor(self, color: QColor) -> None:
        self._color = color
        self.update()
    
    def setPulse(self, enabled: bool) -> None:
        self._pulse_enabled = enabled
        if enabled:
            self._start_pulse()
    
    def _start_pulse(self) -> None:
        if not self._pulse_enabled:
            return
        
        from PySide6.QtCore import QTimer
        self._pulse_opacity = 1.0
        
        def animate():
            if not self._pulse_enabled:
                return
            self._pulse_opacity = (self._pulse_opacity - 0.05) % 1.0
            self.update()
        
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(animate)
        self._pulse_timer.start(50)
    
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        color = self._color
        
        # Glow effect
        if self._pulse_enabled:
            glow_color = QColor(color)
            glow_color.setAlpha(int(50 * self._pulse_opacity))
            painter.setBrush(glow_color)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(-3, -3, self.width() + 6, self.height() + 6)
        
        painter.setBrush(color)
        painter.drawEllipse(0, 0, self.width(), self.height())


class ModernCheckBox(QWidget):
    """Modern checkbox with toggle style option."""
    toggled = Signal(bool)
    
    def __init__(self, parent=None, text: str = "", use_toggle: bool = False) -> None:
        super().__init__(parent)
        self._text = text
        self._use_toggle = use_toggle
        self._checked = False
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        if use_toggle:
            self._toggle = Toggle()
            self._toggle.toggled.connect(self._on_toggle)
            layout.addWidget(self._toggle)
        else:
            self._checkbox = QCheckBox()
            self._checkbox.toggled.connect(self._on_toggle)
            layout.addWidget(self._checkbox)
        
        if text:
            self._label = QLabel(text)
            self._label.setCursor(Qt.PointingHandCursor)
            self._label.mousePressEvent = lambda e: self.toggle()
            layout.addWidget(self._label)
        
        layout.addStretch(1)
    
    def _on_toggle(self, checked: bool) -> None:
        self._checked = checked
        self.toggled.emit(checked)
    
    def toggle(self) -> None:
        self.setChecked(not self._checked)
    
    def setChecked(self, checked: bool) -> None:
        if self._use_toggle:
            self._toggle.setChecked(checked)
        else:
            self._checkbox.setChecked(checked)
        self._checked = checked
    
    def isChecked(self) -> bool:
        return self._checked


class FadeInWidget(QWidget):
    """Widget with fade-in animation."""
    def __init__(self, parent=None, duration: int = 300) -> None:
        super().__init__(parent)
        self._duration = duration
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0)
        self.setGraphicsEffect(self._opacity_effect)
    
    def fadeIn(self) -> None:
        animation = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        animation.setDuration(self._duration)
        animation.setStartValue(0)
        animation.setEndValue(1)
        animation.start()
    
    def fadeOut(self, callback=None) -> None:
        animation = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        animation.setDuration(self._duration)
        animation.setStartValue(1)
        animation.setEndValue(0)
        animation.start()
        if callback:
            animation.finished.connect(callback)
