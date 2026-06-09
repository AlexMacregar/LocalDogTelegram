from __future__ import annotations

import os
import sys
import webbrowser
import subprocess
import json
import random
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer, QThread, Signal, QRect
from PySide6.QtGui import QAction, QColor, QGuiApplication, QKeySequence, QCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGroupBox,
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QSystemTrayIcon,
    QToolTip,
    QTabWidget,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)

from localdog import __app_name__, __version__
from localdog.proxy import build_link, proxy_config
from localdog.proxy.config import (
    save_config,
    load_config,
    GITHUB_RELEASES_URL,
)
from localdog.proxy.stats import human_bytes, human_speed, stats
from localdog.ui.icon import (
    make_icon,
    make_tray_icon,
    make_gear_icon,
    make_update_icon,
    make_copy_icon,
    make_refresh_icon,
    make_play_icon,
    make_stop_icon,
    make_test_icon,
)
from localdog.ui.log_bridge import LogBridge, install as install_log_bridge
from localdog.ui.runner import ProxyRunner
from localdog.ui import theme
from localdog.ui.theme import set_theme, stylesheet
from localdog.ui.i18n import tr, set_language
from localdog.ui.components import Toggle, StatusIndicator

print("[DEBUG] window.py imported")

def _hr() -> QFrame:
    f = QFrame()
    f.setObjectName("hr")
    return f

def _stat(label_text: str) -> tuple[QWidget, QLabel]:
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(4)
    value = QLabel("0")
    value.setObjectName("stat_value")
    lab = QLabel(label_text)
    lab.setObjectName("stat_label")
    lay.addWidget(value)
    lay.addWidget(lab)
    return box, value

class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        print("[DEBUG] MainWindow.__init__ start")
        self.setObjectName("root")
        self.setWindowTitle(__app_name__)
        self.setMinimumSize(QSize(500, 850))
        self.resize(560, 930)
        self.setWindowIcon(make_icon())

        self.runner = ProxyRunner()
        self.log_bridge = LogBridge()
        install_log_bridge(self.log_bridge, verbose=proxy_config.verbose)

        self.proxy_running = False
        self._toggling = False
        self._synced = False

        self._build_ui()
        self._wire()

        self._refresh_link()
        self._set_state("off")

        self._stats_timer = QTimer(self)
        self._stats_timer.setInterval(1000)
        self._stats_timer.timeout.connect(self._refresh_stats)
        self._stats_timer.start()

        if proxy_config.minimize_to_tray_on_start:
            QTimer.singleShot(0, self.hide)

        self._start_update_checker()

        # Auto-start proxy if configured
        if proxy_config.auto_start:
            QTimer.singleShot(500, self._start_proxy_if_needed)

        print("[DEBUG] MainWindow.__init__ end")

    def _start_proxy_if_needed(self):
        if not self.proxy_running:
            self._toggle_proxy()

    # ------------------------------- UI Building ---------------------------------
    def _build_ui(self) -> None:
        print("[DEBUG] _build_ui")
        self.stacked = QStackedWidget(self)
        self.home_page = QWidget()
        self.settings_page = QWidget()
        self.stacked.addWidget(self.home_page)
        self.stacked.addWidget(self.settings_page)

        self._build_home_page()
        self._build_settings_page()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.stacked)

    def _build_home_page(self) -> None:
        print("[DEBUG] _build_home_page")
        layout = QVBoxLayout(self.home_page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        brand_box = QVBoxLayout()
        brand_box.setSpacing(2)
        brand = QLabel(__app_name__)
        brand.setObjectName("h1")
        sub = QLabel(f"@Alex_Macregar · v{__version__}")
        sub.setObjectName("faint")
        brand_box.addWidget(brand)
        brand_box.addWidget(sub)
        top_bar.addLayout(brand_box, 1)

        self.update_btn = QPushButton()
        self.update_btn.setObjectName("update_btn")
        self.update_btn.setIcon(make_update_icon(20, QColor(theme.COLORS["text_dim"])))
        self.update_btn.setIconSize(QSize(20, 20))
        self.update_btn.setFixedSize(36, 36)
        self.update_btn.setCursor(Qt.PointingHandCursor)
        self.update_btn.setToolTip(tr("check_updates"))
        top_bar.addWidget(self.update_btn, 0, Qt.AlignVCenter)

        self.gear_btn = QPushButton()
        self.gear_btn.setObjectName("gear_btn")
        self.gear_btn.setIcon(make_gear_icon(24, QColor(theme.COLORS["text_dim"])))
        self.gear_btn.setIconSize(QSize(22, 22))
        self.gear_btn.setFixedSize(36, 36)
        self.gear_btn.setCursor(Qt.PointingHandCursor)
        top_bar.addWidget(self.gear_btn, 0, Qt.AlignVCenter)

        layout.addLayout(top_bar)

        layout.addStretch(1)

        power_container = QHBoxLayout()
        power_container.setAlignment(Qt.AlignCenter)
        self.toggle_btn = QPushButton("⏻")
        self.toggle_btn.setObjectName("power_btn")
        self.toggle_btn.setFixedSize(150, 150)
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.setShortcut(QKeySequence("Ctrl+R"))
        power_container.addWidget(self.toggle_btn)
        layout.addLayout(power_container)

        status_box = QHBoxLayout()
        status_box.setAlignment(Qt.AlignCenter)
        status_box.setSpacing(8)
        self.status_dot = StatusIndicator(size=8)
        self.status_pill = QLabel(tr("offline").upper())
        self.status_pill.setObjectName("status_home")
        status_box.addWidget(self.status_dot)
        status_box.addWidget(self.status_pill)
        layout.addLayout(status_box)

        layout.addStretch(2)

        link_card = QFrame()
        link_card.setObjectName("card")
        lc = QVBoxLayout(link_card)
        lc.setContentsMargins(18, 16, 18, 16)
        lc.setSpacing(10)

        lc_title = QLabel(tr("connection_link"))
        lc_title.setObjectName("h2")
        lc.addWidget(lc_title)

        self.link_btn = QPushButton("")
        self.link_btn.setObjectName("link_btn")
        self.link_btn.setCursor(Qt.PointingHandCursor)
        self.link_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        lc.addWidget(self.link_btn)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.open_btn = QPushButton(tr("open_in_telegram"))
        self.copy_btn = QPushButton(tr("copy"))
        self.copy_btn.setObjectName("copy_btn")
        self.regen_btn = QPushButton(tr("new_secret"))
        self.regen_btn.setObjectName("regen_btn")
        actions.addWidget(self.open_btn)
        actions.addWidget(self.copy_btn)
        actions.addWidget(self.regen_btn)
        actions.addStretch(1)
        lc.addLayout(actions)

        layout.addWidget(link_card)

    def _build_settings_page(self) -> None:
        print("[DEBUG] _build_settings_page")
        layout = QVBoxLayout(self.settings_page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        top_bar = QHBoxLayout()
        self.back_btn = QPushButton(tr("back"))
        self.back_btn.setObjectName("back_btn")
        self.back_btn.setCursor(Qt.PointingHandCursor)
        top_bar.addWidget(self.back_btn)
        top_bar.addStretch(1)
        layout.addLayout(top_bar)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self._build_stats_tab(), tr("stats"))
        self.tabs.addTab(self._build_settings_tab_inner(), tr("settings"))
        self.tabs.addTab(self._build_cloudflare_tab(), tr("cloudflare"))
        self.tabs.addTab(self._build_log_tab(), tr("log"))
        layout.addWidget(self.tabs, 1)

    def _build_stats_tab(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 8, 0, 8)
        lay.setSpacing(16)

        title = QLabel(tr("live"))
        title.setObjectName("h2")
        lay.addWidget(title)

        grid = QHBoxLayout()
        grid.setSpacing(28)

        self.s_active, self.lbl_active = _stat(tr("active"))
        self.s_total, self.lbl_total = _stat(tr("served"))
        self.s_ws, self.lbl_ws = _stat(tr("via_ws"))
        self.s_tcp, self.lbl_tcp = _stat(tr("via_tcp"))

        for w in (self.s_active, self.s_total, self.s_ws, self.s_tcp):
            grid.addWidget(w)
        grid.addStretch(1)
        lay.addLayout(grid)

        lay.addWidget(_hr())

        traffic = QHBoxLayout()
        traffic.setSpacing(28)
        self.s_up, self.lbl_up = _stat(tr("uploaded"))
        self.s_down, self.lbl_down = _stat(tr("downloaded"))
        traffic.addWidget(self.s_up)
        traffic.addWidget(self.s_down)
        traffic.addStretch(1)
        lay.addLayout(traffic)

        speed_box = QWidget()
        speed_lay = QHBoxLayout(speed_box)
        speed_lay.setSpacing(28)
        self.s_speed_up = QLabel("0 B/s")
        self.s_speed_up.setObjectName("stat_value")
        self.s_speed_down = QLabel("0 B/s")
        self.s_speed_down.setObjectName("stat_value")
        
        self.lbl_speed_up_wrap, self.lbl_speed_up = self._labeled_speed(tr("speed_up"), self.s_speed_up)
        self.lbl_speed_down_wrap, self.lbl_speed_down = self._labeled_speed(tr("speed_down"), self.s_speed_down)
        
        speed_lay.addWidget(self.lbl_speed_up_wrap)
        speed_lay.addWidget(self.lbl_speed_down_wrap)
        speed_lay.addStretch(1)
        lay.addWidget(speed_box)

        lay.addStretch(1)

        self.hint_label = QLabel(tr("hint_text"))
        self.hint_label.setObjectName("faint")
        self.hint_label.setWordWrap(True)
        lay.addWidget(self.hint_label)

        return page

    def _labeled_speed(self, text: str, widget: QWidget) -> tuple[QWidget, QLabel]:
        wrap = QWidget()
        v = QVBoxLayout(wrap)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        lab = QLabel(text)
        lab.setObjectName("stat_label")
        v.addWidget(lab)
        v.addWidget(widget)
        return wrap, lab

    def _add_help(self, layout: QHBoxLayout, help_key: str) -> None:
        btn = QPushButton("?")
        btn.setObjectName("help_btn")
        btn.setToolTip(tr(help_key))
        btn.setCursor(Qt.PointingHandCursor)
        # Force tooltip to show instantly on click and stay longer
        btn.clicked.connect(lambda: QToolTip.showText(QCursor.pos(), tr(help_key), btn, QRect(), 5000))
        layout.addWidget(btn)

    def _build_settings_tab_inner(self) -> QWidget:
        page = QWidget()
        page_lay = QVBoxLayout(page)
        page_lay.setContentsMargins(12, 12, 12, 12)
        page_lay.setSpacing(0)

        container = QWidget()
        container.setObjectName("settings_container")
        container_lay = QVBoxLayout(container)
        container_lay.setContentsMargins(0, 0, 0, 0)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        scroll = QVBoxLayout(content)
        scroll.setContentsMargins(20, 16, 20, 20)
        scroll.setSpacing(20)

        # ===== CONNECTION SECTION =====
        conn_section_row = QHBoxLayout()
        self.conn_section = QLabel(tr("connection"))
        self.conn_section.setObjectName("section_header")
        conn_section_row.addWidget(self.conn_section)
        conn_section_row.addStretch(1)
        self._add_help(conn_section_row, "help_connection")
        scroll.addLayout(conn_section_row)

        # Host & Port Card
        conn_card = QFrame()
        conn_card.setObjectName("icon_card")
        conn_layout = QHBoxLayout(conn_card)
        conn_layout.setContentsMargins(16, 14, 16, 14)
        conn_layout.setSpacing(16)

        self.in_host = QLineEdit(proxy_config.host)
        self.in_host.setPlaceholderText("127.0.0.1")
        self.in_host.setFixedWidth(180)

        self.in_port = QSpinBox()
        self.in_port.setRange(1, 65535)
        self.in_port.setValue(proxy_config.port)
        self.in_port.setFixedWidth(100)

        self.lbl_host = QLabel(tr("host"))
        self.lbl_port = QLabel(tr("port"))
        conn_layout.addWidget(self.lbl_host)
        conn_layout.addWidget(self.in_host, 1)
        conn_layout.addWidget(self.lbl_port)
        conn_layout.addWidget(self.in_port)
        scroll.addWidget(conn_card)

        # Secret Card
        secret_card = QFrame()
        secret_card.setObjectName("icon_card")
        secret_layout = QVBoxLayout(secret_card)
        secret_layout.setContentsMargins(16, 14, 16, 14)
        secret_layout.setSpacing(8)

        secret_header = QHBoxLayout()
        self.lbl_secret = QLabel(tr("secret"))
        secret_header.addWidget(self.lbl_secret)
        secret_header.addStretch(1)
        self.regen_secret_btn = QPushButton(tr("new_secret"))
        self.regen_secret_btn.setObjectName("ghost")
        self.regen_secret_btn.clicked.connect(self._regen_secret)
        secret_header.addWidget(self.regen_secret_btn)
        secret_layout.addLayout(secret_header)

        self.in_secret = QLineEdit(proxy_config.secret)
        self.in_secret.setPlaceholderText(tr("secret"))
        secret_layout.addWidget(self.in_secret)
        scroll.addWidget(secret_card)

        # DC Routing Card
        dc_card = QFrame()
        dc_card.setObjectName("icon_card")
        dc_layout = QVBoxLayout(dc_card)
        dc_layout.setContentsMargins(16, 14, 16, 14)
        dc_layout.setSpacing(8)

        dc_header = QHBoxLayout()
        self.lbl_dc = QLabel(tr("dc_routing"))
        dc_header.addWidget(self.lbl_dc)
        dc_header.addStretch(1)
        self.load_dc_btn = QPushButton(tr("load_dc_from_github"))
        self.load_dc_btn.setObjectName("ghost")
        dc_header.addWidget(self.load_dc_btn)
        dc_layout.addLayout(dc_header)

        self.in_dc = QPlainTextEdit()
        dc_text = "\n".join(f"{dc}:{','.join(proxy_config.dc_ip_lists.get(dc, [ip]))}"
                            for dc, ip in proxy_config.dc_redirects.items())
        self.in_dc.setPlainText(dc_text)
        self.in_dc.setPlaceholderText("2:149.154.167.220,149.154.167.221\n4:149.154.167.220")
        self.in_dc.setFixedHeight(80)
        dc_layout.addWidget(self.in_dc)
        scroll.addWidget(dc_card)

        # ===== PERFORMANCE SECTION =====
        perf_section_row = QHBoxLayout()
        self.perf_section = QLabel(tr("performance"))
        self.perf_section.setObjectName("section_header")
        perf_section_row.addWidget(self.perf_section)
        perf_section_row.addStretch(1)
        self._add_help(perf_section_row, "help_performance")
        scroll.addLayout(perf_section_row)

        perf_card = QFrame()
        perf_card.setObjectName("icon_card")
        perf_layout = QHBoxLayout(perf_card)
        perf_layout.setContentsMargins(16, 12, 16, 12)
        perf_layout.setSpacing(24)

        buf_widget = QWidget()
        buf_layout = QVBoxLayout(buf_widget)
        buf_layout.setContentsMargins(0, 0, 0, 0)
        buf_layout.setSpacing(4)
        self.lbl_buffer = QLabel(tr("buffer"))
        self.lbl_buffer.setObjectName("settings_label")
        self.in_buf = QSpinBox()
        self.in_buf.setRange(16, 4096)
        self.in_buf.setValue(proxy_config.buffer_kb)
        self.in_buf.setSuffix(" KB")
        self.in_buf.setFixedWidth(100)
        buf_layout.addWidget(self.lbl_buffer)
        buf_layout.addWidget(self.in_buf)
        perf_layout.addWidget(buf_widget)

        pool_widget = QWidget()
        pool_layout = QVBoxLayout(pool_widget)
        pool_layout.setContentsMargins(0, 0, 0, 0)
        pool_layout.setSpacing(4)
        self.lbl_pool = QLabel(tr("ws_pool"))
        self.lbl_pool.setObjectName("settings_label")
        self.in_pool = QSpinBox()
        self.in_pool.setRange(0, 32)
        self.in_pool.setValue(proxy_config.pool_size)
        self.in_pool.setFixedWidth(80)
        pool_layout.addWidget(self.lbl_pool)
        pool_layout.addWidget(self.in_pool)
        perf_layout.addWidget(pool_widget)

        perf_layout.addStretch(1)
        scroll.addWidget(perf_card)

        # ===== INTERFACE SECTION =====
        ui_section_row = QHBoxLayout()
        self.ui_section = QLabel(tr("interface"))
        self.ui_section.setObjectName("section_header")
        ui_section_row.addWidget(self.ui_section)
        ui_section_row.addStretch(1)
        self._add_help(ui_section_row, "help_interface")
        scroll.addLayout(ui_section_row)

        # Auto Start Card
        self.auto_start_toggle = Toggle()
        self.auto_start_toggle.setChecked(proxy_config.auto_start)
        auto_card = QFrame()
        auto_card.setObjectName("icon_card")
        auto_layout = QHBoxLayout(auto_card)
        auto_layout.setContentsMargins(16, 12, 16, 12)
        auto_layout.setSpacing(12)
        self.lbl_auto_start = QLabel(tr("auto_start_hint"))
        self.lbl_auto_start.setObjectName("icon_card_title")
        auto_layout.addWidget(self.lbl_auto_start, 1)
        auto_layout.addWidget(self.auto_start_toggle)
        scroll.addWidget(auto_card)

        # Minimize to Tray Card
        self.minimize_tray_toggle = Toggle()
        self.minimize_tray_toggle.setChecked(proxy_config.minimize_to_tray_on_start)
        tray_card = QFrame()
        tray_card.setObjectName("icon_card")
        tray_layout = QHBoxLayout(tray_card)
        tray_layout.setContentsMargins(16, 12, 16, 12)
        tray_layout.setSpacing(12)
        self.lbl_minimize_tray = QLabel(tr("minimize_to_tray_hint"))
        self.lbl_minimize_tray.setObjectName("icon_card_title")
        tray_layout.addWidget(self.lbl_minimize_tray, 1)
        tray_layout.addWidget(self.minimize_tray_toggle)
        scroll.addWidget(tray_card)

        # Verbose Logging Card
        self.verbose_toggle = Toggle()
        self.verbose_toggle.setChecked(proxy_config.verbose)
        verb_card = QFrame()
        verb_card.setObjectName("icon_card")
        verb_layout = QHBoxLayout(verb_card)
        verb_layout.setContentsMargins(16, 12, 16, 12)
        verb_layout.setSpacing(12)
        self.lbl_verbose = QLabel(tr("verbose_logging"))
        self.lbl_verbose.setObjectName("icon_card_title")
        verb_layout.addWidget(self.lbl_verbose, 1)
        verb_layout.addWidget(self.verbose_toggle)
        scroll.addWidget(verb_card)

        # Fake TLS Card
        self.fake_tls_toggle = Toggle()
        self.fake_tls_toggle.setChecked(proxy_config.fake_tls)
        tls_card = QFrame()
        tls_card.setObjectName("icon_card")
        tls_layout = QHBoxLayout(tls_card)
        tls_layout.setContentsMargins(16, 12, 16, 12)
        tls_layout.setSpacing(12)
        self.lbl_fake_tls = QLabel(tr("fake_tls"))
        self.lbl_fake_tls.setObjectName("icon_card_title")
        tls_layout.addWidget(self.lbl_fake_tls, 1)
        tls_layout.addWidget(self.fake_tls_toggle)
        scroll.addWidget(tls_card)

        # Theme Card
        theme_card = QFrame()
        theme_card.setObjectName("icon_card")
        theme_layout = QHBoxLayout(theme_card)
        theme_layout.setContentsMargins(16, 12, 16, 12)
        theme_layout.setSpacing(12)
        self.lbl_theme = QLabel(tr("theme"))
        theme_layout.addWidget(self.lbl_theme)
        theme_layout.addStretch(1)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light", "system"])
        self.theme_combo.setCurrentText(proxy_config.theme)
        theme_layout.addWidget(self.theme_combo)
        scroll.addWidget(theme_card)

        # Language Card
        lang_card = QFrame()
        lang_card.setObjectName("icon_card")
        lang_layout = QHBoxLayout(lang_card)
        lang_layout.setContentsMargins(16, 12, 16, 12)
        lang_layout.setSpacing(12)
        self.lbl_lang = QLabel(tr("language"))
        lang_layout.addWidget(self.lbl_lang)
        lang_layout.addStretch(1)
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["ru", "en"])
        self.lang_combo.setCurrentText(proxy_config.language)
        lang_layout.addWidget(self.lang_combo)
        scroll.addWidget(lang_card)

        # ===== ACTIONS SECTION =====
        actions_section_row = QHBoxLayout()
        self.actions_section = QLabel(tr("actions"))
        self.actions_section.setObjectName("section_header")
        actions_section_row.addWidget(self.actions_section)
        actions_section_row.addStretch(1)
        self._add_help(actions_section_row, "help_actions")
        scroll.addLayout(actions_section_row)

        actions_card = QFrame()
        actions_card.setObjectName("icon_card")
        actions_layout = QHBoxLayout(actions_card)
        actions_layout.setContentsMargins(16, 12, 16, 12)
        actions_layout.setSpacing(12)

        self.export_btn = QPushButton(tr("export_config"))
        self.import_btn = QPushButton(tr("import_config"))
        actions_layout.addWidget(self.export_btn)
        actions_layout.addWidget(self.import_btn)
        actions_layout.addStretch(1)
        scroll.addWidget(actions_card)

        # Save/Reset buttons
        foot = QHBoxLayout()
        self.save_btn = QPushButton(tr("save"))
        self.save_btn.setObjectName("primary")
        self.cancel_btn = QPushButton(tr("reset"))
        foot.addStretch(1)
        foot.addWidget(self.cancel_btn)
        foot.addWidget(self.save_btn)
        scroll.addLayout(foot)

        scroll.addStretch(1)
        scroll_area.setWidget(content)
        container_lay.addWidget(scroll_area)
        page_lay.addWidget(container)
        return page

    def _build_cloudflare_tab(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 8, 0, 8)
        lay.setSpacing(12)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel(tr("cf_mode") + ":"))
        self.cf_mode_combo = QComboBox()
        self.cf_mode_combo.addItems(["off", "cf_proxy", "cf_worker"])
        self.cf_mode_combo.setCurrentText(proxy_config.cf_mode)
        mode_row.addWidget(self.cf_mode_combo)
        mode_row.addStretch(1)
        lay.addLayout(mode_row)

        cf_proxy_row = QHBoxLayout()
        cf_proxy_row.addWidget(QLabel(tr("cf_proxy_domain") + ":"))
        self.cf_domain_edit = QLineEdit(proxy_config.cf_domain)
        self.cf_domain_edit.setPlaceholderText("example.com")
        cf_proxy_row.addWidget(self.cf_domain_edit, 1)
        lay.addLayout(cf_proxy_row)

        cf_worker_row = QHBoxLayout()
        cf_worker_row.addWidget(QLabel(tr("cf_worker_domain") + ":"))
        self.cf_worker_edit = QLineEdit(proxy_config.cf_worker_domain)
        self.cf_worker_edit.setPlaceholderText("your-worker.workers.dev")
        cf_worker_row.addWidget(self.cf_worker_edit, 1)
        lay.addLayout(cf_worker_row)

        hint = QLabel(tr("cf_hint"))
        hint.setObjectName("faint")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        lay.addStretch(1)

        foot = QHBoxLayout()
        self.save_cf_btn = QPushButton(tr("save_cf"))
        self.save_cf_btn.setObjectName("primary")
        foot.addStretch(1)
        foot.addWidget(self.save_cf_btn)
        lay.addLayout(foot)

        return page

    def _build_log_tab(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 8, 0, 8)
        lay.setSpacing(10)

        head = QHBoxLayout()
        t = QLabel(tr("log"))
        t.setObjectName("h2")
        head.addWidget(t)
        head.addStretch(1)
        self.clear_log_btn = QPushButton(tr("clear"))
        self.clear_log_btn.setObjectName("ghost")
        head.addWidget(self.clear_log_btn)
        lay.addLayout(head)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(3000)
        lay.addWidget(self.log_view, 1)
        return page

    def _labeled(self, text: str, widget: QWidget) -> QWidget:
        wrap = QWidget()
        v = QVBoxLayout(wrap)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        lab = QLabel(text)
        lab.setObjectName("stat_label")
        v.addWidget(lab)
        v.addWidget(widget)
        return wrap

    # ------------------------------- Signals ---------------------------------
    def _wire(self) -> None:
        print("[DEBUG] _wire")
        self.toggle_btn.clicked.connect(self._toggle_proxy)
        self.gear_btn.clicked.connect(lambda: self.stacked.setCurrentIndex(1))
        self.back_btn.clicked.connect(lambda: self.stacked.setCurrentIndex(0))
        self.copy_btn.clicked.connect(self._copy_link)
        self.link_btn.clicked.connect(self._copy_link)
        self.open_btn.clicked.connect(self._open_in_telegram)
        self.regen_btn.clicked.connect(self._regen_secret)
        self.save_btn.clicked.connect(self._save_settings)
        self.cancel_btn.clicked.connect(self._reload_settings)
        self.save_cf_btn.clicked.connect(self._save_cf_settings)
        self.clear_log_btn.clicked.connect(self.log_view.clear)
        self.log_bridge.line.connect(self._append_log)
        self.runner.started.connect(self._on_proxy_started)
        self.runner.stopped.connect(self._on_proxy_stopped)
        self.runner.failed.connect(self._on_failed)
        self.update_btn.clicked.connect(self._manual_update_check)
        self.lang_combo.currentTextChanged.connect(self._change_language)
        self.export_btn.clicked.connect(self._export_config)
        self.import_btn.clicked.connect(self._import_config)
        self.load_dc_btn.clicked.connect(self._load_dc_from_github)
        
        # Sync changes from settings to main screen
        self.in_host.textChanged.connect(lambda: self._apply_settings_silently())
        self.in_port.valueChanged.connect(lambda: self._apply_settings_silently())
        self.in_secret.textChanged.connect(lambda: self._apply_settings_silently())

    # ------------------------------- Proxy state -----------------------------
    def _on_proxy_started(self):
        print("[DEBUG] _on_proxy_started")
        self.proxy_running = True
        self._set_state("on")
        if hasattr(self, 'tray_controller'):
            self.tray_controller._refresh_menu()

    def _on_proxy_stopped(self):
        print("[DEBUG] _on_proxy_stopped")
        self.proxy_running = False
        self._set_state("off")
        self.toggle_btn.setEnabled(True)
        if hasattr(self, 'tray_controller'):
            self.tray_controller._refresh_menu()

    def _toggle_proxy(self) -> None:
        if self._toggling:
            return
        self._toggling = True
        try:
            print(f"[DEBUG] _toggle_proxy called, proxy_running={self.proxy_running}")
            if self.proxy_running:
                print("[DEBUG] Stopping proxy...")
                self.toggle_btn.setEnabled(False)
                self.runner.stop()
                QTimer.singleShot(3000, lambda: self.toggle_btn.setEnabled(True))
                QTimer.singleShot(500, self._force_stop_sync)
                # Сброс флага через 2.5 секунды, чтобы не блокировать повторный старт
                QTimer.singleShot(2500, lambda: setattr(self, '_toggling', False))
            else:
                print("[DEBUG] Starting proxy...")
                self._apply_settings_silently()
                self.runner.start()
                QTimer.singleShot(2000, lambda: setattr(self, '_toggling', False))
        except Exception as e:
            print(f"[DEBUG] Error in _toggle_proxy: {e}")
            self._toggling = False

    def _force_stop_sync(self) -> None:
        if self._synced:
            return
        self._synced = True
        try:
            print(f"[DEBUG] _force_stop_sync: proxy_running={self.proxy_running}, runner.is_running={self.runner.is_running()}")
            if self.proxy_running and not self.runner.is_running():
                self.proxy_running = False
                self._set_state("off")
                self.toggle_btn.setEnabled(True)
                if hasattr(self, 'tray_controller'):
                    self.tray_controller._refresh_menu()
                print("[DEBUG] _force_stop_sync: state synced")
        finally:
            QTimer.singleShot(500, lambda: setattr(self, '_synced', False))

    def _set_state(self, state: str) -> None:
        print(f"[DEBUG] _set_state {state}")
        if state == "on":
            text = tr("online").upper()
            self.toggle_btn.setProperty("state", "on")
            self.status_pill.setProperty("state", "on")
            self.status_dot.setColor(QColor(theme.COLORS["ok"]))
            self.status_dot.setPulse(True)
        elif state == "off":
            text = tr("offline").upper()
            self.toggle_btn.setProperty("state", "off")
            self.status_pill.setProperty("state", "off")
            self.status_dot.setColor(QColor(theme.COLORS["text_faint"]))
            self.status_dot.setPulse(False)
        else:
            text = tr("error").upper()
            self.toggle_btn.setProperty("state", "err")
            self.status_pill.setProperty("state", "err")
            self.status_dot.setColor(QColor(theme.COLORS["err"]))
            self.status_dot.setPulse(False)
        self.status_pill.setText(text)
        self.toggle_btn.style().unpolish(self.toggle_btn)
        self.toggle_btn.style().polish(self.toggle_btn)
        self.status_pill.style().unpolish(self.status_pill)
        self.status_pill.style().polish(self.status_pill)

    # ------------------------------- Actions ---------------------------------
    def _copy_link(self) -> None:
        link = build_link(proxy_config.host, proxy_config.port, proxy_config.secret)
        QGuiApplication.clipboard().setText(link)
        prev = self.copy_btn.text()
        self.copy_btn.setText(tr("copied"))
        QTimer.singleShot(1100, lambda: self.copy_btn.setText(prev))

    def _open_in_telegram(self) -> None:
        link = build_link(proxy_config.host, proxy_config.port, proxy_config.secret)
        webbrowser.open(link)

    def _regen_secret(self) -> None:
        proxy_config.secret = os.urandom(16).hex()
        self.in_secret.setText(proxy_config.secret)
        self._refresh_link()
        save_config()

    def _refresh_link(self) -> None:
        link = build_link(proxy_config.host, proxy_config.port, proxy_config.secret)
        self.link_btn.setText(link)
        self.link_btn.setToolTip(tr("copy"))

    def _refresh_stats(self) -> None:
        stats.update_speed()
        self.lbl_active.setText(str(stats.connections_active))
        self.lbl_total.setText(str(stats.connections_total))
        self.lbl_ws.setText(str(stats.connections_ws))
        self.lbl_tcp.setText(str(stats.connections_tcp))
        self.lbl_up.setText(human_bytes(stats.bytes_up))
        self.lbl_down.setText(human_bytes(stats.bytes_down))
        self.s_speed_up.setText(human_speed(stats.speed_up))
        self.s_speed_down.setText(human_speed(stats.speed_down))

    def _append_log(self, line: str) -> None:
        self.log_view.appendPlainText(line)

    # ------------------------------- Settings --------------------------------
    def _save_settings(self) -> None:
        try:
            self._apply_settings()
            save_config()
            self._refresh_link()
            QMessageBox.information(self, "LocalDog", tr("settings_saved"))
            if self.proxy_running:
                self._restart_proxy()
        except ValueError as e:
            QMessageBox.warning(self, "LocalDog", str(e))

    def _apply_settings_silently(self) -> None:
        try:
            # Sync to config object
            proxy_config.host = self.in_host.text().strip() or "127.0.0.1"
            proxy_config.port = int(self.in_port.value())
            proxy_config.secret = self.in_secret.text().strip()
            # Update link on home page
            self._refresh_link()
        except Exception:
            pass

    def _apply_settings(self, update_autostart: bool = True) -> None:
        proxy_config.host = self.in_host.text().strip() or "127.0.0.1"
        proxy_config.port = int(self.in_port.value())
        
        if proxy_config.port == 443 and sys.platform == "win32":
            log.warning("Port 443 on Windows often requires Admin rights or is occupied by System service.")
        
        secret = self.in_secret.text().strip()
        if secret:
            if len(secret) != 32:
                raise ValueError("Secret must be 32 hex chars")
            try:
                bytes.fromhex(secret)
                proxy_config.secret = secret
            except ValueError:
                raise ValueError("Secret must be valid hex")

        new_dc_redirects = {}
        new_dc_ip_lists = {}
        for line in self.in_dc.toPlainText().splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if ':' not in line:
                continue
            dc_part, ips_part = line.split(':', 1)
            try:
                dc = int(dc_part)
                ips = [ip.strip() for ip in ips_part.split(',') if ip.strip()]
                if ips:
                    new_dc_redirects[dc] = ips[0]
                    new_dc_ip_lists[dc] = ips
            except ValueError:
                pass
        if not new_dc_redirects:
            raise ValueError("at least one DC entry is required")
        proxy_config.dc_redirects = new_dc_redirects
        proxy_config.dc_ip_lists = new_dc_ip_lists

        proxy_config.buffer_kb = int(self.in_buf.value())
        proxy_config.pool_size = int(self.in_pool.value())
        proxy_config.verbose = self.verbose_toggle.isChecked()

        old_auto_start = proxy_config.auto_start
        proxy_config.auto_start = self.auto_start_toggle.isChecked()
        proxy_config.minimize_to_tray_on_start = self.minimize_tray_toggle.isChecked()
        proxy_config.fake_tls = self.fake_tls_toggle.isChecked()

        old_theme = proxy_config.theme
        proxy_config.theme = self.theme_combo.currentText()
        if old_theme != proxy_config.theme:
            self._apply_theme()

        if update_autostart and old_auto_start != proxy_config.auto_start:
            self._set_auto_start(proxy_config.auto_start)

    def _apply_theme(self) -> None:
        set_theme(proxy_config.theme)
        app = QApplication.instance()
        if app:
            app.setStyleSheet(stylesheet())
        
        # Re-color icons
        self.update_btn.setIcon(make_update_icon(20, QColor(theme.COLORS["text_dim"])))
        self.gear_btn.setIcon(make_gear_icon(24, QColor(theme.COLORS["text_dim"])))
        self.back_btn.setIcon(make_back_icon(18, QColor(theme.COLORS["text"])))
        
        # Update status dot if needed
        if self.proxy_running:
            self.status_dot.setColor(QColor(theme.COLORS["ok"]))
        else:
            self.status_dot.setColor(QColor(theme.COLORS["text_faint"]))

    def _set_auto_start(self, enabled: bool) -> None:
        if sys.platform != "win32":
            return
        startup_folder = Path(os.getenv("APPDATA")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        shortcut_path = startup_folder / "LocalDog.lnk"
        startup_folder.mkdir(parents=True, exist_ok=True)

        if not enabled:
            if shortcut_path.exists():
                shortcut_path.unlink()
            return

        if getattr(sys, 'frozen', False):
            target = sys.executable
            args = ""
        else:
            target = sys.executable
            args = "-m localdog"
        working_dir = str(Path(target).parent if getattr(sys, 'frozen', False) else Path.cwd())

        ps_code = f'''
$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{target}"
$Shortcut.Arguments = "{args}"
$Shortcut.WorkingDirectory = "{working_dir}"
$Shortcut.Save()
'''
        try:
            subprocess.run(['powershell', '-Command', ps_code], capture_output=True, check=False)
        except Exception:
            pass

    def _save_settings(self) -> None:
        was_running = self.proxy_running
        try:
            self._apply_settings(update_autostart=True)
        except ValueError as exc:
            QMessageBox.warning(self, "LocalDog", str(exc))
            return
        save_config()
        self._refresh_link()
        self.save_btn.setText(tr("saved"))
        QTimer.singleShot(1100, lambda: self.save_btn.setText(tr("save")))

        if was_running:
            QTimer.singleShot(200, lambda: self._restart_proxy())

    def _restart_proxy(self):
        if self.proxy_running:
            self.runner.stop()
            QTimer.singleShot(500, lambda: self.runner.start())

    def _save_cf_settings(self) -> None:
        proxy_config.cf_mode = self.cf_mode_combo.currentText()
        proxy_config.cf_domain = self.cf_domain_edit.text().strip()
        proxy_config.cf_worker_domain = self.cf_worker_edit.text().strip()
        save_config()
        self.save_cf_btn.setText(tr("saved"))
        QTimer.singleShot(1100, lambda: self.save_cf_btn.setText(tr("save_cf")))
        if self.proxy_running:
            QTimer.singleShot(200, lambda: self._restart_proxy())

    def _reload_settings(self) -> None:
        self.in_host.setText(proxy_config.host)
        self.in_port.setValue(proxy_config.port)
        self.in_secret.setText(proxy_config.secret)
        dc_text = "\n".join(f"{dc}:{','.join(proxy_config.dc_ip_lists.get(dc, [ip]))}"
                            for dc, ip in proxy_config.dc_redirects.items())
        self.in_dc.setPlainText(dc_text)
        self.in_buf.setValue(proxy_config.buffer_kb)
        self.in_pool.setValue(proxy_config.pool_size)
        self.verbose_toggle.setChecked(proxy_config.verbose)
        self.auto_start_toggle.setChecked(proxy_config.auto_start)
        self.minimize_tray_toggle.setChecked(proxy_config.minimize_to_tray_on_start)
        self.theme_combo.setCurrentText(proxy_config.theme)
        self.cf_mode_combo.setCurrentText(proxy_config.cf_mode)
        self.cf_domain_edit.setText(proxy_config.cf_domain)
        self.cf_worker_edit.setText(proxy_config.cf_worker_domain)
        self.lang_combo.setCurrentText(proxy_config.language)
        self.fake_tls_toggle.setChecked(proxy_config.fake_tls)
        self._refresh_link()

    def _on_failed(self, message: str) -> None:
        self._set_state("err")
        QMessageBox.critical(self, "LocalDog", message)

    # ------------------------------- I18n ------------------------------------
    def _change_language(self, lang: str) -> None:
        set_language(lang)
        proxy_config.language = lang
        save_config()
        self._reload_ui_texts()

    def _reload_ui_texts(self):
        self.setWindowTitle(__app_name__)
        self.update_btn.setToolTip(tr("check_updates"))
        self.open_btn.setText(tr("open_in_telegram"))
        self.copy_btn.setText(tr("copy"))
        self.regen_btn.setText(tr("new_secret"))
        self.back_btn.setText(tr("back"))
        self.save_btn.setText(tr("save"))
        self.cancel_btn.setText(tr("reset"))
        self.clear_log_btn.setText(tr("clear"))
        self.export_btn.setText(tr("export_config"))
        self.import_btn.setText(tr("import_config"))
        self.load_dc_btn.setText(tr("load_dc_from_github"))
        self.save_cf_btn.setText(tr("save_cf"))
        self.tabs.setTabText(0, tr("stats"))
        self.tabs.setTabText(1, tr("settings"))
        self.tabs.setTabText(2, tr("cloudflare"))
        self.tabs.setTabText(3, tr("log"))
        
        # Update stats labels
        self.lbl_active.setText(tr("active"))
        self.lbl_total.setText(tr("served"))
        self.lbl_ws.setText(tr("via_ws"))
        self.lbl_tcp.setText(tr("via_tcp"))
        self.lbl_up.setText(tr("uploaded"))
        self.lbl_down.setText(tr("downloaded"))
        self.lbl_speed_up.setText(tr("speed_up"))
        self.lbl_speed_down.setText(tr("speed_down"))
        self.hint_label.setText(tr("hint_text"))
        
        # Update settings labels
        if hasattr(self, "conn_section"):
            self.conn_section.setText(tr("connection"))
            self.perf_section.setText(tr("performance"))
            self.ui_section.setText(tr("interface"))
            self.actions_section.setText(tr("actions"))
            self.lbl_host.setText(tr("host"))
            self.lbl_port.setText(tr("port"))
            self.lbl_secret.setText(tr("secret"))
            self.lbl_dc.setText(tr("dc_routing"))
            self.lbl_buffer.setText(tr("buffer"))
            self.lbl_pool.setText(tr("ws_pool"))
            self.lbl_auto_start.setText(tr("auto_start_hint"))
            self.lbl_minimize_tray.setText(tr("minimize_to_tray_hint"))
            self.lbl_verbose.setText(tr("verbose_logging"))
            self.lbl_fake_tls.setText(tr("fake_tls"))
            self.lbl_theme.setText(tr("theme"))
            self.lbl_lang.setText(tr("language"))

        if self.proxy_running:
            self._set_state("on")
        else:
            self._set_state("off")
        self._refresh_link()

    # ------------------------------- Import/Export ---------------------------
    def _export_config(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Config", "localdog_config.json", "JSON (*.json)")
        if path:
            save_config()
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(proxy_config.__dict__, f, indent=2, default=str)
                QMessageBox.information(self, "Export", "Config exported successfully")
            except Exception as e:
                QMessageBox.warning(self, "Export Error", str(e))

    def _import_config(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Config", "", "JSON (*.json)")
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for key, value in data.items():
                    if hasattr(proxy_config, key):
                        setattr(proxy_config, key, value)
                save_config()
                self._reload_settings()
                QMessageBox.information(self, "Import", "Config imported successfully")
            except Exception as e:
                QMessageBox.warning(self, "Import Error", str(e))

    # ------------------------------- DC Loader ------------------------------
    def _load_dc_from_github(self):
        QMessageBox.information(self, "Loading", "Fetching DC servers from GitHub...")
        class DcLoaderThread(QThread):
            finished = Signal(dict)
            def run(self):
                try:
                    import requests
                    url = "https://raw.githubusercontent.com/AlexMacregar/LocalDogTelegram/main/DCServers.txt"
                    resp = requests.get(url, timeout=10)
                    if resp.status_code == 200:
                        servers = {}
                        for line in resp.text.splitlines():
                            line = line.strip()
                            if not line or line.startswith('#'):
                                continue
                            if ':' not in line:
                                continue
                            dc_part, ips_part = line.split(':', 1)
                            try:
                                dc = int(dc_part)
                                ips = [ip.strip() for ip in ips_part.split(',') if ip.strip()]
                                if ips:
                                    servers[dc] = ips
                            except ValueError:
                                continue
                        self.finished.emit(servers)
                except Exception:
                    self.finished.emit({})
        self.dc_thread = DcLoaderThread()
        self.dc_thread.finished.connect(self._on_dc_loaded)
        self.dc_thread.start()

    def _on_dc_loaded(self, servers: dict):
        if not servers:
            QMessageBox.warning(self, "Error", "Failed to load DC servers from GitHub.")
            return
        new_redirects = {}
        new_lists = {}
        for dc, ips in servers.items():
            if ips:
                new_redirects[dc] = ips[0]
                new_lists[dc] = ips
        if new_redirects:
            proxy_config.dc_redirects = new_redirects
            proxy_config.dc_ip_lists = new_lists
            save_config()
            self._reload_settings()
            QMessageBox.information(self, "Success", f"Loaded {len(new_redirects)} DC servers.")
        else:
            QMessageBox.warning(self, "Error", "No valid DC entries found.")

    # ------------------------------- Update Checker --------------------------
    def _start_update_checker(self) -> None:
        try:
            import requests
        except ImportError:
            return
        self._update_check_timer = QTimer(self)
        self._update_check_timer.setInterval(3600000)
        self._update_check_timer.timeout.connect(self._check_updates)
        self._update_check_timer.start()
        QTimer.singleShot(2000, self._check_updates)

    def _manual_update_check(self) -> None:
        self._check_updates(manual=True)

    def _check_updates(self, manual: bool = False) -> None:
        class UpdateThread(QThread):
            result = Signal(str, str)
            no_update = Signal()
            error = Signal(str)
            
            def __init__(self, manual_check: bool):
                super().__init__()
                self.manual_check = manual_check

            def run(self):
                try:
                    import requests
                    resp = requests.get(GITHUB_RELEASES_URL, timeout=10)
                    if resp.status_code == 200:
                        data = resp.json()
                        latest = data["tag_name"].lstrip('v')
                        if latest != __version__:
                            self.result.emit(latest, data["html_url"])
                        elif self.manual_check:
                            self.no_update.emit()
                    elif self.manual_check:
                        self.error.emit(f"HTTP {resp.status_code}")
                except Exception as e:
                    if self.manual_check:
                        self.error.emit(str(e))
        
        self._update_thread = UpdateThread(manual)
        self._update_thread.result.connect(self._on_new_version)
        self._update_thread.no_update.connect(lambda: QMessageBox.information(self, __app_name__, tr("no_updates")))
        self._update_thread.error.connect(lambda msg: QMessageBox.warning(self, __app_name__, f"{tr('update_error')}: {msg}"))
        self._update_thread.start()

    def _on_new_version(self, version: str, url: str) -> None:
        self._new_version_url = url
        self.update_btn.setIcon(make_update_icon(20, QColor(COLORS["accent"])))
        self.update_btn.setToolTip(tr("update_available").format(version=version))
        if hasattr(self, 'tray_controller'):
            self.tray_controller.tray.showMessage(
                __app_name__,
                tr("update_available").format(version=version),
                QSystemTrayIcon.Information,
                5000
            )

    def _open_releases_page(self) -> None:
        if hasattr(self, '_new_version_url'):
            webbrowser.open(self._new_version_url)

    # ------------------------------- Close event -----------------------------
    def closeEvent(self, event):
        """Override close event: hide window instead of closing."""
        event.ignore()
        self.hide()


class TrayController:
    def __init__(self, window: MainWindow):
        self.window = window
        self.tray = QSystemTrayIcon(make_tray_icon(), parent=window)
        self.tray.setToolTip(__app_name__)
        self.tray.activated.connect(self._on_activated)
        self._build_menu()
        self.tray.show()
        window.tray_controller = self

    def _build_menu(self) -> None:
        from PySide6.QtWidgets import QMenu

        self.menu = QMenu()
        self.act_toggle = QAction(tr("start"), self.menu)
        self.act_toggle.triggered.connect(self.window._toggle_proxy)
        self.act_open = QAction(tr("open_window"), self.menu)
        self.act_open.triggered.connect(self._show)
        self.act_copy = QAction(tr("copy_link"), self.menu)
        self.act_copy.triggered.connect(self.window._copy_link)
        self.act_tg = QAction(tr("open_in_telegram"), self.menu)
        self.act_tg.triggered.connect(self.window._open_in_telegram)
        self.act_quit = QAction(tr("quit"), self.menu)
        self.act_quit.triggered.connect(QApplication.instance().quit)

        self.menu.addAction(self.act_toggle)
        self.menu.addAction(self.act_open)
        self.menu.addSeparator()
        self.menu.addAction(self.act_copy)
        self.menu.addAction(self.act_tg)
        self.menu.addSeparator()
        self.menu.addAction(self.act_quit)
        self.tray.setContextMenu(self.menu)
        self._refresh_menu()

    def _refresh_menu(self) -> None:
        running = self.window.proxy_running
        self.act_toggle.setText(tr("stop") if running else tr("start"))

    def _show(self) -> None:
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def _on_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._show()


def run_app() -> int:
    print("[DEBUG] run_app start")
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("LocalDog")
    set_language(proxy_config.language)
    set_theme(proxy_config.theme)
    app.setStyleSheet(stylesheet())

    load_config()

    win = MainWindow()
    tray = TrayController(win)
    win.show()
    print("[DEBUG] window shown")
    return app.exec()