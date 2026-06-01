#!/usr/bin/env python3
"""EFT Shelter Helper — Помощник по убежищу Escape from Tarkov"""

import sys
import json
from pathlib import Path
from collections import defaultdict
from typing import Optional, Dict, List, Tuple

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QScrollArea, QGridLayout, QFrame, QLabel, QPushButton,
    QSpinBox, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QDialog, QMessageBox, QListWidget,
    QGroupBox, QLayout, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QSize, QPoint
from PyQt6.QtGui import QColor, QPalette, QPainter, QPixmap

# When frozen by PyInstaller, data files live next to the .exe, not inside
# the temporary unpack dir — resolve relative to the executable in that case.
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).parent
else:
    APP_DIR = Path(__file__).parent
DATA_FILE = APP_DIR / "hideout_data.json"
USER_FILE = APP_DIR / "user_data.json"
ASSETS_DIR = APP_DIR / "assets"
IMAGES_FILE = ASSETS_DIR / "item_images.json"

# ── Palette ────────────────────────────────────────────────────────────────────
C_BG      = "#0d1117"
C_BG2     = "#161b22"
C_BG3     = "#21262d"
C_BORDER  = "#30363d"
C_ACCENT  = "#c8a96e"
C_TEXT    = "#e6edf3"
C_MUTED   = "#7d8590"
C_GREEN   = "#3fb950"
C_YELLOW  = "#d29922"
C_RED     = "#f85149"
C_GBG     = "#0d2218"
C_YBG     = "#201a0a"
C_RBG     = "#200d0d"

STYLE = f"""
* {{ font-family: "Segoe UI", Arial, sans-serif; font-size: 15px; }}
QMainWindow, QDialog, QWidget {{ background: {C_BG}; color: {C_TEXT}; }}
QTabWidget::pane {{ border: 1px solid {C_BORDER}; background: {C_BG}; top:-1px; }}
QTabBar::tab {{
    background: {C_BG2}; color: {C_MUTED};
    padding: 10px 22px; border: 1px solid {C_BORDER};
    border-bottom: none; margin-right: 2px; border-radius: 4px 4px 0 0;
}}
QTabBar::tab:selected {{ background:{C_BG3}; color:{C_ACCENT}; font-weight:bold; border-bottom: 2px solid {C_ACCENT}; }}
QTabBar::tab:hover:!selected {{ background:{C_BG3}; color:{C_TEXT}; }}
QScrollArea {{ background:transparent; border:none; }}
QScrollBar:vertical {{ background:{C_BG2}; width:8px; border:none; }}
QScrollBar::handle:vertical {{ background:{C_BORDER}; border-radius:4px; min-height:20px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
QPushButton {{
    background:{C_BG3}; color:{C_TEXT}; border:1px solid {C_BORDER};
    border-radius:4px; padding:6px 14px; font-weight:500;
}}
QPushButton:hover {{ border-color:{C_ACCENT}; color:{C_ACCENT}; }}
QPushButton:disabled {{ background:{C_BG2}; color:{C_MUTED}; border-color:{C_BG3}; }}
QSpinBox {{
    background:{C_BG2}; color:{C_TEXT}; border:1px solid {C_BORDER};
    border-radius:4px; padding:4px 6px; min-width:70px;
}}
QSpinBox:focus {{ border-color:{C_ACCENT}; }}
QSpinBox::up-button, QSpinBox::down-button {{ background:{C_BG3}; border:none; width:20px; }}
QLineEdit {{
    background:{C_BG2}; color:{C_TEXT}; border:1px solid {C_BORDER};
    border-radius:4px; padding:6px 10px;
}}
QLineEdit:focus {{ border-color:{C_ACCENT}; }}
QLabel {{ background:transparent; color:{C_TEXT}; }}
QGroupBox {{
    background:{C_BG2}; border:1px solid {C_BORDER};
    border-radius:6px; margin-top:26px; padding:10px;
}}
QGroupBox::title {{
    color:{C_ACCENT}; subcontrol-origin:margin;
    left:10px; top:4px; padding:0 4px; background:{C_BG2};
}}
QTableWidget {{
    background:{C_BG}; alternate-background-color:{C_BG2};
    gridline-color:{C_BORDER}; border:1px solid {C_BORDER}; border-radius:4px;
    selection-background-color:{C_BG3};
}}
QHeaderView::section {{
    background:{C_BG2}; color:{C_MUTED}; padding:8px;
    border:none; border-right:1px solid {C_BORDER}; border-bottom:1px solid {C_BORDER};
    font-weight:bold;
}}
QListWidget {{
    background:{C_BG2}; border:1px solid {C_BORDER}; border-radius:4px;
}}
QListWidget::item {{ padding:4px 8px; }}
QListWidget::item:hover {{ background:{C_BG3}; }}
QListWidget::item:selected {{ background:{C_ACCENT}; color:{C_BG}; }}
QComboBox {{
    background:{C_BG2}; color:{C_TEXT}; border:1px solid {C_BORDER};
    border-radius:4px; padding:5px 10px;
}}
QComboBox QAbstractItemView {{
    background:{C_BG2}; color:{C_TEXT}; selection-background-color:{C_BG3};
    border:1px solid {C_BORDER};
}}
QToolTip {{
    background:{C_BG3}; color:{C_TEXT}; border:1px solid {C_BORDER};
    padding:6px 10px; border-radius:4px;
}}
"""

# ── Known module names (for dep parsing) ─────────────────────────────────────
MODULE_NAMES = {
    "Аварийная стена","Безопасность","Библиотека","Биткоин ферма",
    "Вентиляция","Верстак","Водосборник","Воздушный Фильтратор",
    "Генератор","Зона Отдыха","Медблок","Обогрев","Оружейный стенд",
    "Освещение","Пищеблок","Разведцентр","Самогонный Аппарат",
    "Санузел","Склад","Солнечная Батарея","Тир","Тренажерный зал",
    "Ящик Диких","Круг сектантов","Стенд со снаряжением",
    "Уголок боевой славы","Елка",
}
# lowercase alias map to handle case inconsistencies in wiki data
_LOWER_MAP = {n.lower(): n for n in MODULE_NAMES}
_LOWER_MAP["зона отдыха"] = "Зона Отдыха"


def _parse_dep(dep_str: str):
    """'Some Module Ур N' → (normalized_name, level) or None"""
    idx = dep_str.rfind(" Ур ")
    if idx < 0:
        return None
    name_part = dep_str[:idx].strip()
    level_part = dep_str[idx + 4:].strip()
    try:
        level = int(level_part)
    except ValueError:
        return None
    normalized = _LOWER_MAP.get(name_part.lower())
    if normalized:
        return (normalized, level)
    return None


# ── Module icons (emoji fallbacks) ───────────────────────────────────────────
MODULE_ICONS = {
    "Аварийная стена":    "🧱", "Безопасность":       "🔒",
    "Библиотека":         "📚", "Биткоин ферма":       "💰",
    "Вентиляция":         "💨", "Верстак":             "🔧",
    "Водосборник":        "💧", "Воздушный Фильтратор":"🌬",
    "Генератор":          "⚡", "Зона Отдыха":         "🛋",
    "Медблок":            "🏥", "Обогрев":             "🔥",
    "Оружейный стенд":    "🔫", "Освещение":           "💡",
    "Пищеблок":           "🍳", "Разведцентр":         "📡",
    "Самогонный Аппарат": "🥃", "Санузел":             "🚿",
    "Склад":              "📦", "Солнечная Батарея":   "☀",
    "Тир":                "🎯", "Тренажерный зал":     "💪",
    "Ящик Диких":         "📫", "Круг сектантов":      "⭕",
    "Стенд со снаряжением":"🎽", "Уголок боевой славы": "🏆",
    "Елка":               "🎄",
}


# ═══════════════════════════════════════════════════════════════════════════════
# Data model
# ═══════════════════════════════════════════════════════════════════════════════
class AppData:
    def __init__(self):
        self.hideout: Dict[str, list] = {}
        self.user_levels: Dict[str, int] = {}
        self.inventory: Dict[str, int] = {}
        self.item_images: Dict[str, str] = {}
        self._load_hideout()
        self._load_user()
        self._load_images()

    def _load_images(self):
        if IMAGES_FILE.exists():
            try:
                self.item_images = json.loads(IMAGES_FILE.read_text("utf-8"))
            except Exception:
                self.item_images = {}

    def icon_path(self, name: str) -> Optional[str]:
        rel = self.item_images.get(name)
        if not rel:
            return None
        p = ASSETS_DIR / rel
        return str(p) if p.exists() else None

    # ── loading ────────────────────────────────────────────────────────────────
    def _load_hideout(self):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        for module, levels in raw.items():
            processed = []
            for lvl in levels:
                mod_deps, skill_deps = [], []
                for d in lvl.get("deps", []):
                    parsed = _parse_dep(d)
                    if parsed:
                        mod_deps.append(parsed)
                    else:
                        skill_deps.append(d)
                processed.append({
                    "level":      lvl["level"],
                    "items":      lvl.get("items", []),
                    "mod_deps":   mod_deps,
                    "skill_deps": skill_deps,
                    "buildTime":  lvl.get("buildTime", ""),
                })
            self.hideout[module] = processed
            self.user_levels.setdefault(module, 0)
        # Stash is available from the start
        self.user_levels.setdefault("Склад", 1)

    def _load_user(self):
        if USER_FILE.exists():
            try:
                data = json.loads(USER_FILE.read_text("utf-8"))
                saved_levels = data.get("levels", {})
                # Only update levels for known modules
                for m in self.hideout:
                    if m in saved_levels:
                        self.user_levels[m] = int(saved_levels[m])
                self.inventory.update(
                    {k: int(v) for k, v in data.get("inventory", {}).items()}
                )
            except Exception:
                pass

    def save(self):
        USER_FILE.write_text(
            json.dumps({"levels": self.user_levels, "inventory": self.inventory},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ── helpers ───────────────────────────────────────────────────────────────
    def max_level(self, m: str) -> int:
        levels = self.hideout.get(m, [])
        return max((l["level"] for l in levels), default=0)

    def cur_level(self, m: str) -> int:
        return self.user_levels.get(m, 0)

    def level_data(self, m: str, lvl: int) -> Optional[dict]:
        for l in self.hideout.get(m, []):
            if l["level"] == lvl:
                return l
        return None

    def deps_ok(self, mod_deps: list) -> bool:
        return all(self.user_levels.get(dep_m, 0) >= dep_l for dep_m, dep_l in mod_deps)

    def can_upgrade(self, m: str) -> bool:
        cur = self.cur_level(m)
        ld = self.level_data(m, cur + 1)
        return ld is not None and self.deps_ok(ld["mod_deps"])

    def has_items(self, m: str) -> bool:
        cur = self.cur_level(m)
        ld = self.level_data(m, cur + 1)
        if not ld:
            return False
        return all(
            self.inventory.get(i["name"], 0) >= i["qty"]
            for i in ld["items"] if i.get("type") != "money"
        )

    def do_upgrade(self, m: str) -> bool:
        cur = self.cur_level(m)
        ld = self.level_data(m, cur + 1)
        if not ld or not self.can_upgrade(m):
            return False
        for i in ld["items"]:
            if i.get("type") == "money":
                continue
            name, qty = i["name"], i["qty"]
            self.inventory[name] = max(0, self.inventory.get(name, 0) - qty)
            if self.inventory[name] == 0:
                del self.inventory[name]
        self.user_levels[m] = cur + 1
        self.save()
        return True

    def all_needed(self) -> dict:
        """item_name → {'now': qty, 'later': qty}"""
        result: Dict[str, dict] = defaultdict(lambda: {"now": 0, "later": 0})
        for m, levels in self.hideout.items():
            cur = self.cur_level(m)
            for ld in levels:
                if ld["level"] <= cur:
                    continue
                is_now = (ld["level"] == cur + 1) and self.deps_ok(ld["mod_deps"])
                key = "now" if is_now else "later"
                for i in ld["items"]:
                    if i.get("type") == "money":
                        continue
                    result[i["name"]][key] += i["qty"]
        return result

    def all_item_names(self) -> List[str]:
        items: set[str] = set()
        for m, levels in self.hideout.items():
            cur = self.cur_level(m)
            for ld in levels:
                if ld["level"] <= cur:
                    continue
                for i in ld["items"]:
                    if i.get("type") != "money":
                        items.add(i["name"])
        items.update(k for k, v in self.inventory.items() if v > 0)
        return sorted(items)


# ═══════════════════════════════════════════════════════════════════════════════
# Flow layout (wraps tiles to the available width)
# ═══════════════════════════════════════════════════════════════════════════════
class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=6):
        super().__init__(parent)
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self._items: list = []

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, i):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _do_layout(self, rect, test_only):
        x, y, line_h = rect.x(), rect.y(), 0
        sp = self.spacing()
        for item in self._items:
            w, h = item.sizeHint().width(), item.sizeHint().height()
            nx = x + w + sp
            if nx - sp > rect.right() and line_h > 0:
                x = rect.x()
                y = y + line_h + sp
                nx = x + w + sp
                line_h = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), QSize(w, h)))
            x = nx
            line_h = max(line_h, h)
        return y + line_h - rect.y()


# ═══════════════════════════════════════════════════════════════════════════════
# Item tile (icon + have/need counter, name as tooltip)
# ═══════════════════════════════════════════════════════════════════════════════
_PIX_CACHE: Dict[Tuple[str, int], QPixmap] = {}

TILE_W, TILE_H, ICON_PX = 66, 84, 54


def _load_pixmap(path: str, size: int) -> Optional[QPixmap]:
    key = (path, size)
    if key in _PIX_CACHE:
        return _PIX_CACHE[key]
    pix = QPixmap(path)
    if pix.isNull():
        return None
    pix = pix.scaled(
        size, size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    _PIX_CACHE[key] = pix
    return pix


_MONEY_GLYPH = {"Рубли": "₽", "Доллары": "$", "Евро": "€"}


class ItemTile(QFrame):
    def __init__(self, name: str, have: int, need: int,
                 icon_path: Optional[str], is_money: bool = False):
        super().__init__()
        self.setObjectName("ItemTile")
        self.setFixedSize(TILE_W, TILE_H)

        ok = is_money or have >= need
        col = C_GREEN if ok else C_RED
        self.setStyleSheet(
            f"QFrame#ItemTile {{ background:{C_BG3}; border:1px solid {col};"
            f" border-radius:5px; }}"
        )
        if is_money:
            tip = f"{name}: {need:,}".replace(",", " ")
        else:
            tip = f"{name}\nЕсть {have} из {need}"
        self.setToolTip(tip)

        v = QVBoxLayout(self)
        v.setContentsMargins(2, 4, 2, 3)
        v.setSpacing(2)

        icon = QLabel()
        icon.setFixedSize(ICON_PX, ICON_PX)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("background:transparent; border:none;")
        pix = _load_pixmap(icon_path, ICON_PX) if icon_path else None
        if pix:
            icon.setPixmap(pix)
        else:
            icon.setText(_MONEY_GLYPH.get(name, "₽") if is_money else "❔")
            icon.setStyleSheet(
                f"background:transparent; border:none; color:{C_MUTED};"
                f" font-size:{28 if is_money else 22}px;"
            )
        v.addWidget(icon, 0, Qt.AlignmentFlag.AlignHCenter)

        if is_money:
            amt = f"{need:,}".replace(",", " ")
            txt = f"{amt} {_MONEY_GLYPH.get(name, '₽')}"
        else:
            txt = f"{have}/{need} {'✓' if ok else '✗'}"
        cnt = QLabel(txt)
        cnt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cnt.setStyleSheet(
            f"color:{col}; font-size:11px; font-weight:bold;"
            f" background:transparent; border:none;"
        )
        v.addWidget(cnt)


# ═══════════════════════════════════════════════════════════════════════════════
# Module card widget
# ═══════════════════════════════════════════════════════════════════════════════
class ModuleCard(QFrame):
    upgrade_requested = pyqtSignal(str)

    def __init__(self, module: str, data: AppData):
        super().__init__()
        self.module = module
        self.data = data
        self.setObjectName("ModuleCard")
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(4)

        # ── header ─────────────────────────────────────────────────────────
        header = QHBoxLayout()
        icon = QLabel(MODULE_ICONS.get(self.module, "◆"))
        icon.setStyleSheet("font-size:20px; background:transparent;")
        icon.setFixedWidth(28)
        self.name_lbl = QLabel(self.module)
        self.name_lbl.setStyleSheet("font-weight:bold; font-size:15px;")
        self.name_lbl.setWordWrap(True)
        self.lvl_lbl = QLabel()
        self.lvl_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lvl_lbl.setStyleSheet(f"font-size:13px; color:{C_ACCENT}; font-weight:bold;")
        header.addWidget(icon)
        header.addWidget(self.name_lbl, 1)
        header.addWidget(self.lvl_lbl)
        lay.addLayout(header)

        # ── dots bar ───────────────────────────────────────────────────────
        dots_w = QWidget()
        dots_w.setFixedHeight(16)
        self.dots_lay = QHBoxLayout(dots_w)
        self.dots_lay.setContentsMargins(0, 0, 0, 0)
        self.dots_lay.setSpacing(4)
        lay.addWidget(dots_w)

        # ── "ТРЕБОВАНИЯ ДЛЯ УРОВНЯ N" sub-header ────────────────────────────
        self.req_lbl = QLabel()
        self.req_lbl.setStyleSheet(
            f"color:{C_MUTED}; font-size:11px; font-weight:bold;"
            f" letter-spacing:1px; padding-top:2px;"
        )
        lay.addWidget(self.req_lbl)

        # ── status / dependency text (max level, blocked deps) ──────────────
        self.status_lbl = QLabel()
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setVisible(False)
        lay.addWidget(self.status_lbl)

        # ── item tiles (flow-wrapped) ───────────────────────────────────────
        self.tiles_widget = QWidget()
        self.tiles_lay = FlowLayout(self.tiles_widget, margin=2, spacing=6)
        lay.addWidget(self.tiles_widget)

        # ── button ─────────────────────────────────────────────────────────
        self.btn = QPushButton()
        self.btn.setFixedHeight(28)
        self.btn.clicked.connect(lambda: self.upgrade_requested.emit(self.module))
        lay.addWidget(self.btn)

    def _clear_tiles(self):
        while self.tiles_lay.count():
            it = self.tiles_lay.takeAt(0)
            if it and it.widget():
                it.widget().deleteLater()

    def _add_item_tiles(self, ld: dict):
        for i in ld["items"]:
            is_money = i.get("type") == "money"
            name, qty = i["name"], i["qty"]
            if is_money:
                tile = ItemTile(name, qty, qty, None, is_money=True)
            else:
                have = self.data.inventory.get(name, 0)
                tile = ItemTile(name, have, qty, self.data.icon_path(name))
            self.tiles_lay.addWidget(tile)

    def refresh(self):
        cur = self.data.cur_level(self.module)
        max_l = self.data.max_level(self.module)
        self.lvl_lbl.setText(f"{cur}/{max_l}")

        # dots
        while self.dots_lay.count():
            w = self.dots_lay.takeAt(0).widget()
            if w:
                w.deleteLater()
        for i in range(max_l):
            d = QLabel("●" if i < cur else "○")
            d.setStyleSheet(
                (f"color:{C_ACCENT};" if i < cur else f"color:{C_BORDER};")
                + " font-size:13px; background:transparent;"
            )
            self.dots_lay.addWidget(d)
        self.dots_lay.addStretch()

        if cur >= max_l:
            self._set_style("max")
        elif self.data.can_upgrade(self.module):
            if self.data.has_items(self.module):
                self._set_style("ready")
            else:
                self._set_style("missing")
        else:
            self._set_style("blocked")

    def _set_style(self, state: str):
        cur = self.data.cur_level(self.module)
        next_l = cur + 1
        ld = self.data.level_data(self.module, next_l)

        border_map = {
            "max":     ("#1a3a1a", "#22c55e"),
            "ready":   (C_BG2, C_GREEN),
            "missing": (C_BG2, C_YELLOW),
            "blocked": (C_BG2, C_BORDER),
        }
        bg, border = border_map[state]

        self.setStyleSheet(f"""
            QFrame#ModuleCard {{
                background: {bg};
                border: 1px solid {border};
                border-radius: 6px;
            }}
        """)

        self._clear_tiles()
        self.status_lbl.setVisible(False)

        if state == "max":
            self.req_lbl.setVisible(False)
            self.status_lbl.setText("✓ Максимальный уровень")
            self.status_lbl.setStyleSheet(f"font-size:13px; color:{C_GREEN};")
            self.status_lbl.setVisible(True)
            self.btn.setVisible(False)
            return

        # all upgradeable states share the requirements sub-header + tiles
        mark, mark_col = {
            "ready":   ("✓", C_GREEN),
            "missing": ("✗", C_YELLOW),
            "blocked": ("🔒", C_MUTED),
        }[state]
        self.req_lbl.setVisible(True)
        self.req_lbl.setText(f"ТРЕБОВАНИЯ ДЛЯ УРОВНЯ {next_l:02d}   {mark}")
        self.req_lbl.setStyleSheet(
            f"color:{mark_col}; font-size:11px; font-weight:bold;"
            f" letter-spacing:1px; padding-top:2px;"
        )

        if state == "blocked" and ld:
            deps = [f"⛔ {dm} Ур {dl}" for dm, dl in ld["mod_deps"]
                    if self.data.cur_level(dm) < dl]
            if deps:
                self.status_lbl.setText("   ".join(deps))
                self.status_lbl.setStyleSheet(f"font-size:12px; color:{C_MUTED};")
                self.status_lbl.setVisible(True)

        if ld:
            self._add_item_tiles(ld)

        self.btn.setVisible(True)
        if state == "ready":
            self.btn.setEnabled(True)
            self.btn.setText(f"▲ Прокачать до Ур {next_l}")
            self.btn.setStyleSheet(
                f"background:#0d2d0d; color:{C_GREEN}; border:1px solid {C_GREEN};"
                f"border-radius:4px; padding:4px 8px; font-size:12px;"
            )
        elif state == "missing":
            self.btn.setEnabled(False)
            self.btn.setText(f"→ Ур {next_l} (нет предметов)")
            self.btn.setStyleSheet("font-size:12px;")
        else:  # blocked
            self.btn.setEnabled(False)
            self.btn.setText(f"→ Ур {next_l}")
            self.btn.setStyleSheet("font-size:12px;")


# ═══════════════════════════════════════════════════════════════════════════════
# Modules tab
# ═══════════════════════════════════════════════════════════════════════════════
class ModulesTab(QWidget):
    def __init__(self, data: AppData):
        super().__init__()
        self.data = data
        self.cards: Dict[str, ModuleCard] = {}
        self._build_ui()

    def _sorted_modules(self) -> List[str]:
        """Sort: ready → missing items only → blocked by deps → fully built."""
        def key(m):
            cur = self.data.cur_level(m)
            if cur >= self.data.max_level(m):
                return 3
            elif self.data.can_upgrade(m):
                return 0 if self.data.has_items(m) else 1
            else:
                return 2
        return sorted(self.data.hideout.keys(), key=key)

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 12)
        lay.setSpacing(8)

        # stats bar
        sf = QFrame()
        sf.setFixedHeight(38)
        sf.setStyleSheet(f"background:{C_BG2}; border:1px solid {C_BORDER}; border-radius:4px;")
        sl = QHBoxLayout(sf)
        sl.setContentsMargins(12, 0, 12, 0)
        self.stats_lbl = QLabel()
        self.stats_lbl.setStyleSheet(f"color:{C_MUTED}; font-size:12px;")
        sl.addWidget(self.stats_lbl)
        lay.addWidget(sf)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        container = QWidget()
        self.grid = QGridLayout(container)
        self.grid.setSpacing(8)
        self.grid.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(container)
        lay.addWidget(scroll)

        self.COLS = 3
        for c in range(self.COLS):
            self.grid.setColumnStretch(c, 1)
        self.grid.setRowStretch(99, 1)  # push cards to the top

        for idx, module in enumerate(self._sorted_modules()):
            card = ModuleCard(module, self.data)
            card.upgrade_requested.connect(self._on_upgrade)
            self.cards[module] = card
            self.grid.addWidget(
                card, idx // self.COLS, idx % self.COLS,
                Qt.AlignmentFlag.AlignTop,
            )

        self._refresh_stats()

    def _relayout_cards(self):
        for card in self.cards.values():
            self.grid.removeWidget(card)
        for idx, module in enumerate(self._sorted_modules()):
            self.grid.addWidget(
                self.cards[module], idx // self.COLS, idx % self.COLS,
                Qt.AlignmentFlag.AlignTop,
            )

    def _refresh_stats(self):
        ready = sum(1 for m in self.data.hideout
                    if self.data.can_upgrade(m) and self.data.has_items(m))
        avail = sum(1 for m in self.data.hideout if self.data.can_upgrade(m))
        blocked = sum(1 for m in self.data.hideout
                      if self.data.cur_level(m) < self.data.max_level(m)) - avail
        self.stats_lbl.setText(
            f"🟢 Готово к прокачке: {ready}   "
            f"🟡 Нет предметов: {avail - ready}   "
            f"⛔ Заблокировано: {blocked}"
        )

    def refresh(self):
        for card in self.cards.values():
            card.refresh()
        self._relayout_cards()
        self._refresh_stats()

    def _on_upgrade(self, module: str):
        cur = self.data.cur_level(module)
        ld = self.data.level_data(module, cur + 1)
        if not ld:
            return

        lines = []
        for i in ld["items"]:
            if i.get("type") == "money":
                lines.append(f"  • {i['qty']:,} рублей")
            else:
                have = self.data.inventory.get(i["name"], 0)
                mark = "✓" if have >= i["qty"] else "✗"
                lines.append(f"  {mark} {i['qty']}× {i['name']}  ({have} есть)")

        mb = QMessageBox(self)
        mb.setWindowTitle("Подтверждение прокачки")
        mb.setText(f"<b>Прокачать «{module}» до уровня {cur+1}?</b>")
        if lines:
            mb.setInformativeText("Будут использованы:\n" + "\n".join(lines))
        mb.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        mb.setDefaultButton(QMessageBox.StandardButton.Yes)
        if mb.exec() == QMessageBox.StandardButton.Yes:
            if self.data.do_upgrade(module):
                self.refresh()


# ═══════════════════════════════════════════════════════════════════════════════
# Inventory tab
# ═══════════════════════════════════════════════════════════════════════════════
class InventoryTab(QWidget):
    def __init__(self, data: AppData):
        super().__init__()
        self.data = data
        self._rows: List[dict] = []
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 12)
        lay.setSpacing(8)

        # toolbar
        tb = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 Поиск предмета...")
        self.search.setFixedHeight(34)
        self.search.textChanged.connect(self._apply_filter)
        tb.addWidget(self.search, 1)

        self.flt = QComboBox()
        self.flt.addItems(["Все", "🟢 Нужны сейчас", "🟡 Нужны позже", "🔴 Лишние"])
        self.flt.setFixedWidth(180)
        self.flt.currentIndexChanged.connect(self._apply_filter)
        tb.addWidget(self.flt)

        add_btn = QPushButton("+ Добавить")
        add_btn.setFixedHeight(34)
        add_btn.clicked.connect(self._add_item)
        tb.addWidget(add_btn)
        lay.addLayout(tb)

        # legend
        leg = QHBoxLayout()
        for txt, col in [("🟢 Нужен сейчас", C_GREEN),
                          ("🟡 Нужен позже", C_YELLOW),
                          ("🔴 Лишний", C_RED)]:
            l = QLabel(txt)
            l.setStyleSheet(f"color:{col}; font-size:11px; padding:2px 8px;")
            leg.addWidget(l)
        leg.addStretch()

        hint = QLabel("Двойной клик по строке — изменить количество")
        hint.setStyleSheet(f"color:{C_MUTED}; font-size:11px;")
        leg.addWidget(hint)
        lay.addLayout(leg)

        # table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Предмет", "Есть", "Нужно сейчас", "Нужно позже", "Итого нужно", "Статус"]
        )
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c, w in enumerate([80, 120, 110, 110, 90], start=1):
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(c, w)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.itemDoubleClicked.connect(self._on_double_click)
        self.table.setMinimumHeight(300)
        lay.addWidget(self.table)

        self.refresh()

    def refresh(self):
        needed = self.data.all_needed()
        self._rows = []
        all_items = self.data.all_item_names()

        for name in all_items:
            have = self.data.inventory.get(name, 0)
            n = needed.get(name, {"now": 0, "later": 0})
            now, later = n["now"], n["later"]
            total = now + later

            if total == 0 and have == 0:
                continue

            if total == 0:
                status = "red"
            elif now > 0:
                status = "green"
            else:
                status = "yellow"

            self._rows.append({
                "name": name, "have": have,
                "now": now, "later": later, "total": total,
                "status": status,
            })

        self._apply_filter()

    def _apply_filter(self):
        q = self.search.text().lower()
        fi = self.flt.currentIndex()
        self.table.setRowCount(0)

        for r in self._rows:
            if q and q not in r["name"].lower():
                continue
            if fi == 1 and r["status"] != "green":
                continue
            if fi == 2 and r["status"] != "yellow":
                continue
            if fi == 3 and not (r["have"] > 0 and r["total"] == 0):
                continue
            self._add_row(r)

    def _add_row(self, r: dict):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setRowHeight(row, 30)

        if r["total"] == 0:
            bg, sc, st = QColor(C_RBG), C_RED, "🔴 Лишний"
        elif r["status"] == "green":
            bg, sc = QColor(C_GBG), C_GREEN
            st = ("🟢 Готово" if r["have"] >= r["now"]
                  else f"🟢 Нехватка {r['now'] - r['have']}")
        else:
            bg, sc, st = QColor(C_YBG), C_YELLOW, "🟡 Позже"

        cells = [
            (r["name"],               C_TEXT),
            (str(r["have"]),          C_TEXT),
            (str(r["now"]) if r["now"] > 0 else "—",    C_GREEN if r["now"] > 0 else C_MUTED),
            (str(r["later"]) if r["later"] > 0 else "—", C_YELLOW if r["later"] > 0 else C_MUTED),
            (str(r["total"]) if r["total"] > 0 else "—", C_TEXT),
            (st,                       sc),
        ]
        for col, (text, fg) in enumerate(cells):
            item = QTableWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, r["name"])
            item.setForeground(QColor(fg))
            item.setBackground(bg)
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                if col == 0 else
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            )
            self.table.setItem(row, col, item)

    def _on_double_click(self, item: QTableWidgetItem):
        name = item.data(Qt.ItemDataRole.UserRole)
        if name:
            self._edit_qty(name)

    def _edit_qty(self, name: str):
        cur = self.data.inventory.get(name, 0)
        dlg = QDialog(self)
        dlg.setWindowTitle("Изменить количество")
        dlg.setFixedWidth(320)
        lay = QVBoxLayout(dlg)

        lbl = QLabel(f"<b>{name}</b>")
        lbl.setStyleSheet(f"font-size:14px; color:{C_ACCENT};")
        lay.addWidget(lbl)

        spin = QSpinBox()
        spin.setRange(0, 99999)
        spin.setValue(cur)
        spin.setFixedHeight(36)
        lay.addWidget(spin)

        hint = QLabel("0 — удалить предмет из инвентаря")
        hint.setStyleSheet(f"color:{C_MUTED}; font-size:11px;")
        lay.addWidget(hint)

        btns = QHBoxLayout()
        ok = QPushButton("Сохранить")
        ok.setStyleSheet(
            f"background:#0d2d0d; color:{C_GREEN}; border:1px solid {C_GREEN};"
            f"border-radius:4px; padding:6px 16px;"
        )
        ok.clicked.connect(dlg.accept)
        cancel = QPushButton("Отмена")
        cancel.clicked.connect(dlg.reject)
        btns.addStretch()
        btns.addWidget(cancel)
        btns.addWidget(ok)
        lay.addLayout(btns)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            v = spin.value()
            if v > 0:
                self.data.inventory[name] = v
            else:
                self.data.inventory.pop(name, None)
            self.data.save()
            self.refresh()

    def _add_item(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Добавить предметы в инвентарь")
        dlg.setFixedSize(420, 480)
        lay = QVBoxLayout(dlg)

        srch = QLineEdit()
        srch.setPlaceholderText("Поиск...")
        srch.setFixedHeight(34)
        lay.addWidget(srch)

        lst = QListWidget()
        lst.addItems(self.data.all_item_names())
        lay.addWidget(lst)

        def flt(text):
            for i in range(lst.count()):
                lst.item(i).setHidden(text.lower() not in lst.item(i).text().lower())
        srch.textChanged.connect(flt)

        ql = QHBoxLayout()
        ql.addWidget(QLabel("Количество:"))
        qty = QSpinBox()
        qty.setRange(1, 99999)
        qty.setValue(1)
        qty.setFixedWidth(100)
        ql.addWidget(qty)
        ql.addStretch()
        lay.addLayout(ql)

        btns = QHBoxLayout()
        ok = QPushButton("Добавить")
        ok.setStyleSheet(
            f"background:#0d2d0d; color:{C_GREEN}; border:1px solid {C_GREEN};"
            f"border-radius:4px; padding:6px 16px;"
        )
        ok.clicked.connect(dlg.accept)
        cl = QPushButton("Отмена")
        cl.clicked.connect(dlg.reject)
        btns.addStretch()
        btns.addWidget(cl)
        btns.addWidget(ok)
        lay.addLayout(btns)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            sel = lst.currentItem()
            name = sel.text() if sel else srch.text().strip()
            if name:
                self.data.inventory[name] = self.data.inventory.get(name, 0) + qty.value()
                self.data.save()
                self.refresh()


# ═══════════════════════════════════════════════════════════════════════════════
# Shopping tab
# ═══════════════════════════════════════════════════════════════════════════════
class ShoppingTab(QWidget):
    def __init__(self, data: AppData):
        super().__init__()
        self.data = data
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 12)

        info = QLabel("Предметы которых не хватает — сортировка по приоритету")
        info.setStyleSheet(f"color:{C_MUTED}; font-size:12px; margin-bottom:4px;")
        lay.addWidget(info)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.body = QWidget()
        self.body_lay = QVBoxLayout(self.body)
        self.body_lay.setSpacing(16)
        self.body_lay.setContentsMargins(4, 8, 4, 4)
        scroll.setWidget(self.body)
        lay.addWidget(scroll)

        self.refresh()

    def refresh(self):
        while self.body_lay.count():
            it = self.body_lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

        needed = self.data.all_needed()

        miss_now:  Dict[str, tuple] = {}
        miss_later: Dict[str, tuple] = {}

        for name, n in needed.items():
            have = self.data.inventory.get(name, 0)
            if n["now"] > 0:
                if have < n["now"]:
                    miss_now[name] = (have, n["now"])
            elif n["later"] > 0:
                total = n["later"]
                if have < total:
                    miss_later[name] = (have, total)

        if miss_now:
            self.body_lay.addWidget(self._section(
                f"🟢 Нужно прямо сейчас — {len(miss_now)} предметов",
                miss_now, C_GREEN, C_GBG,
            ))
        else:
            ok = QLabel("✓ Всё есть для текущих прокачек!")
            ok.setStyleSheet(
                f"color:{C_GREEN}; font-size:14px; font-weight:bold; padding:12px;"
            )
            self.body_lay.addWidget(ok)

        if miss_later:
            self.body_lay.addWidget(self._section(
                f"🟡 Для будущих прокачек — {len(miss_later)} предметов",
                miss_later, C_YELLOW, C_YBG,
            ))

        self.body_lay.addStretch()

    def _section(self, title: str, items: dict, color: str, bg: str) -> QGroupBox:
        grp = QGroupBox(title)
        grp.setStyleSheet(f"""
            QGroupBox {{
                background:{bg}; border:1px solid {color};
                border-radius:6px; margin-top:26px; padding:10px;
            }}
            QGroupBox::title {{
                color:{color}; background:{bg};
                subcontrol-origin:margin; left:10px; top:4px; padding:0 6px;
                font-size:15px; font-weight:bold;
            }}
        """)
        gl = QGridLayout(grp)
        gl.setSpacing(4)
        gl.setColumnStretch(0, 1)

        for row_idx, (name, (have, need)) in enumerate(
            sorted(items.items(), key=lambda x: x[1][1] - x[1][0], reverse=True)
        ):
            nl = QLabel(f"• {name}")
            nl.setStyleSheet(f"color:{C_TEXT};")
            ql = QLabel(f"{have} / {need}")
            ql.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if have == 0:
                ql.setStyleSheet(f"color:{C_RED}; font-weight:bold; min-width:60px;")
            elif have < need:
                ql.setStyleSheet(f"color:{C_YELLOW}; font-weight:bold; min-width:60px;")
            else:
                ql.setStyleSheet(f"color:{C_GREEN}; font-weight:bold; min-width:60px;")

            # mini progress bar
            pct = min(1.0, have / need) if need > 0 else 0
            bar = _ProgressBar(pct, color)

            gl.addWidget(nl,  row_idx, 0)
            gl.addWidget(bar, row_idx, 1)
            gl.addWidget(ql,  row_idx, 2)

        return grp


class _ProgressBar(QWidget):
    def __init__(self, pct: float, color: str):
        super().__init__()
        self.pct = pct
        self.color = QColor(color)
        self.setFixedSize(80, 8)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        bg = QColor(C_BORDER)
        p.setBrush(bg)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, self.width(), self.height(), 4, 4)
        if self.pct > 0:
            p.setBrush(self.color)
            w = int(self.width() * self.pct)
            p.drawRoundedRect(0, 0, w, self.height(), 4, 4)
        p.end()


# ═══════════════════════════════════════════════════════════════════════════════
# Setup dialog (first-run + settings)
# ═══════════════════════════════════════════════════════════════════════════════
class SetupDialog(QDialog):
    def __init__(self, data: AppData, parent=None):
        super().__init__(parent)
        self.data = data
        self.setWindowTitle("Настройка уровней убежища")
        self.setMinimumSize(600, 520)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(8)

        title = QLabel("Укажите текущие уровни вашего убежища")
        title.setStyleSheet(
            f"font-size:16px; font-weight:bold; color:{C_ACCENT}; padding:8px 0 4px;"
        )
        lay.addWidget(title)

        sub = QLabel("0 = не построено.  Склад начинается с 1.")
        sub.setStyleSheet(f"color:{C_MUTED}; font-size:11px; margin-bottom:6px;")
        lay.addWidget(sub)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(6)
        grid.setContentsMargins(4, 4, 4, 4)

        self._spins: Dict[str, QSpinBox] = {}
        modules = list(self.data.hideout.keys())

        for idx, m in enumerate(modules):
            icon = QLabel(MODULE_ICONS.get(m, "◆"))
            icon.setFixedWidth(22)
            icon.setStyleSheet("font-size:15px;")
            lbl = QLabel(m)
            spin = QSpinBox()
            spin.setRange(0, self.data.max_level(m))
            spin.setValue(self.data.cur_level(m))
            spin.setFixedWidth(75)
            self._spins[m] = spin

            row, col = idx // 2, (idx % 2) * 3
            grid.addWidget(icon, row, col)
            grid.addWidget(lbl,  row, col + 1)
            grid.addWidget(spin, row, col + 2)

        scroll.setWidget(container)
        lay.addWidget(scroll)

        btns = QHBoxLayout()
        reset_btn = QPushButton("Сбросить всё")
        reset_btn.clicked.connect(self._reset)
        save_btn = QPushButton("Сохранить")
        save_btn.setStyleSheet(
            f"background:#0d2d0d; color:{C_GREEN}; border:1px solid {C_GREEN};"
            f"border-radius:4px; padding:8px 20px;"
        )
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(reset_btn)
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(save_btn)
        lay.addLayout(btns)

    def _reset(self):
        for m, sp in self._spins.items():
            sp.setValue(1 if m == "Склад" else 0)

    def accept(self):
        for m, sp in self._spins.items():
            self.data.user_levels[m] = sp.value()
        self.data.save()
        super().accept()


# ═══════════════════════════════════════════════════════════════════════════════
# Main window
# ═══════════════════════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data = AppData()
        self.setWindowTitle("EFT — Помощник по убежищу")
        self.setMinimumSize(1100, 720)
        self.resize(1340, 820)

        if not USER_FILE.exists():
            self._run_setup()

        self._build_ui()

    def _run_setup(self):
        dlg = SetupDialog(self.data, self)
        dlg.exec()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        rl = QVBoxLayout(root)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        # ── header bar ─────────────────────────────────────────────────────
        hdr = QFrame()
        hdr.setFixedHeight(54)
        hdr.setStyleSheet(
            f"background:{C_BG2}; border-bottom:1px solid {C_BORDER}; border-radius:0;"
        )
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(16, 0, 16, 0)

        logo = QLabel("EFT УБЕЖИЩЕ")
        logo.setStyleSheet(
            f"font-size:20px; font-weight:900; color:{C_ACCENT}; letter-spacing:3px;"
        )
        hl.addWidget(logo)

        sub = QLabel("Помощник по прокачке")
        sub.setStyleSheet(f"color:{C_MUTED}; font-size:11px; margin-left:10px;")
        hl.addWidget(sub)
        hl.addStretch()

        setup_btn = QPushButton("⚙  Уровни убежища")
        setup_btn.clicked.connect(self._open_setup)
        hl.addWidget(setup_btn)

        rl.addWidget(hdr)

        # ── tabs ────────────────────────────────────────────────────────────
        self.tabs = QTabWidget()
        self.modules_tab  = ModulesTab(self.data)
        self.inventory_tab = InventoryTab(self.data)
        self.shopping_tab  = ShoppingTab(self.data)

        self.tabs.addTab(self.modules_tab,   "🏗  Модули убежища")
        self.tabs.addTab(self.inventory_tab, "📦  Инвентарь")
        self.tabs.addTab(self.shopping_tab,  "📋  Что собирать")
        self.tabs.currentChanged.connect(self._on_tab_change)
        rl.addWidget(self.tabs)

    def _on_tab_change(self, idx: int):
        if idx == 0:
            self.modules_tab.refresh()
        elif idx == 1:
            self.inventory_tab.refresh()
        elif idx == 2:
            self.shopping_tab.refresh()

    def _open_setup(self):
        dlg = SetupDialog(self.data, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.modules_tab.refresh()
            self.inventory_tab.refresh()
            self.shopping_tab.refresh()


# ═══════════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    if not DATA_FILE.exists():
        print(f"ERROR: {DATA_FILE} not found")
        return 1

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)

    # Force dark palette
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window,          QColor(C_BG))
    pal.setColor(QPalette.ColorRole.WindowText,      QColor(C_TEXT))
    pal.setColor(QPalette.ColorRole.Base,            QColor(C_BG2))
    pal.setColor(QPalette.ColorRole.AlternateBase,   QColor(C_BG3))
    pal.setColor(QPalette.ColorRole.Text,            QColor(C_TEXT))
    pal.setColor(QPalette.ColorRole.Button,          QColor(C_BG3))
    pal.setColor(QPalette.ColorRole.ButtonText,      QColor(C_TEXT))
    pal.setColor(QPalette.ColorRole.Highlight,       QColor(C_ACCENT))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(C_BG))
    app.setPalette(pal)

    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
