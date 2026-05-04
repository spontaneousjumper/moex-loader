import sys
import os
import json
from datetime import datetime
from typing import List, Tuple, Set

import requests
from openpyxl import Workbook
from openpyxl.styles import numbers

from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QItemSelectionModel, QSettings, QDate, QTime, QDateTime, QSize
)
from PyQt6.QtGui import QColor, QFont, QPalette, QIcon
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QComboBox,
    QDateTimeEdit, QProgressBar, QFileDialog, QMessageBox, QStyleFactory,
    QAbstractItemView, QSizePolicy, QFrame, QCalendarWidget, QDialog,
    QDialogButtonBox, QGridLayout, QSpinBox
)

# ---------- Константы ----------
MOEX_SECURITIES_URL = "https://iss.moex.com/iss/engines/stock/markets/shares/securities.json"
MOEX_CANDLES_URL = "https://iss.moex.com/iss/engines/stock/markets/shares/boards/{}/securities/{}/candles.json"
BOARD = "TQBR"
INTERVALS = [
    ("1", "1 минута"),
    ("10", "10 минут"),
    ("60", "1 час"),
    ("4", "4 часа"),
    ("24", "1 день"),
    ("7", "1 неделя"),
    ("31", "1 месяц"),
]

# ---------- Кэш ----------
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".moex_downloader")
STOCKS_CACHE = os.path.join(CONFIG_DIR, "stocks.json")

def load_cached_stocks():
    try:
        with open(STOCKS_CACHE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def save_stocks(stocks):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(STOCKS_CACHE, "w", encoding="utf-8") as f:
        json.dump(stocks, f, ensure_ascii=False, indent=2)

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ---------- Потоки ----------
class LoadStocksWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self):
        try:
            resp = requests.get(MOEX_SECURITIES_URL, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            securities = data.get("securities", {}).get("data", [])
            columns = data.get("securities", {}).get("columns", [])
            if not securities or not columns:
                raise ValueError("Пустой ответ API")
            idx_secid = columns.index("SECID")
            idx_shortname = columns.index("SHORTNAME")
            idx_boardid = columns.index("BOARDID")
            stocks = []
            for row in securities:
                if row[idx_boardid] == BOARD:
                    stocks.append((row[idx_shortname], row[idx_secid]))
            stocks.sort(key=lambda x: x[1])
            self.finished.emit(stocks)
        except Exception as e:
            self.error.emit(str(e))

class DownloadWorker(QThread):
    log = pyqtSignal(str)
    progress = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, tickers, folder, start_str, end_str, interval):
        super().__init__()
        self.tickers = tickers
        self.folder = folder
        self.start_str = start_str
        self.end_str = end_str
        self.interval = interval

    def run(self):
        total = len(self.tickers)
        for i, ticker in enumerate(self.tickers):
            try:
                self.log.emit(f"Загрузка {ticker}...")
                url = MOEX_CANDLES_URL.format(BOARD, ticker)
                params = {
                    "from": self.start_str,
                    "till": self.end_str,
                    "interval": self.interval,
                    "start": 0,
                    "limit": 5000
                }
                resp = requests.get(url, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                candles = data.get("candles", {}).get("data", [])
                cols = data.get("candles", {}).get("columns", [])

                if not candles:
                    self.log.emit(f"{ticker} — нет данных")
                    self.progress.emit(int((i + 1) / total * 100))
                    continue

                filepath = os.path.join(self.folder, f"{ticker}.xlsx")
                self.save_to_xlsx(ticker, self.interval, candles, cols, filepath)
                self.log.emit(f"Готово: {ticker}")
                self.progress.emit(int((i + 1) / total * 100))
            except Exception as e:
                self.log.emit(f"Ошибка {ticker}: {e}")
                self.progress.emit(int((i + 1) / total * 100))
        self.finished.emit()

    def save_to_xlsx(self, ticker, period, candles, columns, filepath):
        wb = Workbook()
        ws = wb.active
        ws.title = "Котировки"
        ws.append(["TICKER", "PER", "DATETIME", "OPEN", "HIGH", "LOW", "CLOSE", "VOL"])

        idx_open = columns.index("open")
        idx_high = columns.index("high")
        idx_low = columns.index("low")
        idx_close = columns.index("close")
        idx_volume = columns.index("volume")
        idx_begin = columns.index("begin")

        for row in candles:
            begin_dt = datetime.strptime(row[idx_begin], "%Y-%m-%d %H:%M:%S")
            ws.append([
                ticker, period, begin_dt,
                row[idx_open], row[idx_high], row[idx_low],
                row[idx_close], row[idx_volume]
            ])

        # Формат даты через точки
        for cell in ws['C'][1:]:
            cell.number_format = 'DD.MM.YYYY HH:MM:SS'

        wb.save(filepath)

# ---------- Виджет списка с toggle ----------
class ToggleListWidget(QListWidget):
    def selectionCommand(self, index, event=None):
        if event and event.button() == Qt.MouseButton.LeftButton and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            return QItemSelectionModel.SelectionFlag.Toggle
        return super().selectionCommand(index, event)

# ---------- Кастомный DateTimePicker ----------
class DateTimePicker(QWidget):
    dateTimeChanged = pyqtSignal(QDate, QTime)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._date = QDate.currentDate()
        self._time = QTime.currentTime()
        self.init_ui()
        self.update_display()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.line_edit = QLineEdit()
        self.line_edit.setReadOnly(True)
        self.line_edit.setStyleSheet("""
            QLineEdit {
                background-color: #ffffff;
                color: #1e1e1e;
                border: 1px solid #d9d9d9;
                border-top-left-radius: 4px;
                border-bottom-left-radius: 4px;
                border-right: none;
                padding: 4px 8px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #1677ff;
            }
        """)
        self.calendar_btn = QPushButton()
        self.calendar_btn.setText("📅")
        self.calendar_btn.setFixedWidth(32)
        self.calendar_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.calendar_btn.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                color: #333333;
                border: 1px solid #d9d9d9;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                border-left: none;
                padding: 0px;
                font-size: 16px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #e6e6e6;
                border-color: #1677ff;
            }
            QPushButton:pressed {
                background-color: #d9d9d9;
            }
        """)
        self.calendar_btn.clicked.connect(self.show_popup)

        layout.addWidget(self.line_edit)
        layout.addWidget(self.calendar_btn)

    def show_popup(self):
        dlg = DateTimeDialog(self._date, self._time, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._date = dlg.selected_date
            self._time = dlg.selected_time
            self.update_display()
            self.dateTimeChanged.emit(self._date, self._time)

    def update_display(self):
        text = f"{self._date.toString('yyyy-MM-dd')} {self._time.toString('HH:mm')}"
        self.line_edit.setText(text)

    def dateTime(self):
        return QDateTime(self._date, self._time)

    def setDateTime(self, dt: QDateTime):
        self._date = dt.date()
        self._time = dt.time()
        self.update_display()

    def dateTimeString(self, fmt="yyyy-MM-dd HH:mm"):
        return self.dateTime().toString(fmt)

# ---------- Диалог выбора даты и времени ----------
class DateTimeDialog(QDialog):
    def __init__(self, date: QDate, time: QTime, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выберите дату и время")
        self.setFixedSize(400, 320)
        self.selected_date = date
        self.selected_time = time
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ---------- Календарь ----------
        self.calendar = QCalendarWidget()
        self.calendar.setSelectedDate(self.selected_date)
        self.calendar.setGridVisible(False)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)

        pal = self.calendar.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#1e1e1e"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#f5f5f5"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#555555"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#1677ff"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#555555"))
        self.calendar.setPalette(pal)

        self.calendar.setStyleSheet("""
            QCalendarWidget {
                background-color: #ffffff;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #ffffff;
                border-bottom: 1px solid #e0e0e0;
            }
            QCalendarWidget QTableView QHeaderView::section {
                background-color: #f5f5f5;
                color: #555555;
                border: none;
                border-bottom: 1px solid #e0e0e0;
                padding: 4px 0;
                font-size: 12px;
            }
            QCalendarWidget QTableView::item {
                color: #333333;
                background-color: #ffffff;
            }
            QCalendarWidget QTableView::item:selected {
                background-color: #1677ff;
                color: white;
                border-radius: 3px;
            }
            QCalendarWidget QTableView::item:disabled {
                color: #cccccc;
            }
            QCalendarWidget QToolButton {
                color: #333333;
                background-color: transparent;
                border: none;
                padding: 6px;
                font-size: 14px;
            }
            QCalendarWidget QToolButton:hover {
                background-color: #f0f0f0;
                border-radius: 4px;
            }
            QCalendarWidget QComboBox {
                background-color: #ffffff;
                color: #1e1e1e;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                padding: 2px 20px 2px 6px;
            }
            QCalendarWidget QComboBox:hover {
                border-color: #1677ff;
            }
            QCalendarWidget QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #d9d9d9;
                selection-background-color: #1677ff;
                selection-color: white;
            }
            QCalendarWidget QComboBox QAbstractItemView::item {
                color: #1e1e1e;
                background-color: #ffffff;
            }
            QCalendarWidget QComboBox QAbstractItemView::item:selected {
                color: white;
                background-color: #1677ff;
            }
        """)
        layout.addWidget(self.calendar)

        # ---------- Время ----------
        time_layout = QHBoxLayout()
        time_layout.setSpacing(8)

        time_label = QLabel("Время:")
        time_label.setStyleSheet("font-size: 13px; color: #555555;")
        time_layout.addWidget(time_label)

        self.hour_spin = QSpinBox()
        self.hour_spin.setRange(0, 23)
        self.hour_spin.setValue(self.selected_time.hour())
        self.hour_spin.setWrapping(True)
        self.hour_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hour_spin.setFixedWidth(70)
        self.hour_spin.setStyleSheet("""
            QSpinBox {
                background-color: #ffffff;
                color: #1e1e1e;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                padding: 4px 6px;
                font-size: 13px;
            }
            QSpinBox:focus {
                border-color: #1677ff;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 0px;
                height: 0px;
                border: none;
            }
        """)

        self.minute_spin = QSpinBox()
        self.minute_spin.setRange(0, 59)
        self.minute_spin.setValue(self.selected_time.minute())
        self.minute_spin.setWrapping(True)
        self.minute_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.minute_spin.setFixedWidth(70)
        self.minute_spin.setStyleSheet(self.hour_spin.styleSheet())

        time_layout.addWidget(self.hour_spin)
        time_layout.addWidget(QLabel(":"))
        time_layout.addWidget(self.minute_spin)
        time_layout.addStretch()
        layout.addLayout(time_layout)

        # ---------- Кнопки ----------
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)

        button_box.setStyleSheet("""
            QPushButton {
                background-color: #1677ff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 13px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #4096ff;
            }
            QPushButton:pressed {
                background-color: #0958d9;
            }
            QDialogButtonBox QPushButton[text="Cancel"] {
                background-color: #f5f5f5;
                color: #333333;
                border: 1px solid #d9d9d9;
            }
            QDialogButtonBox QPushButton[text="Cancel"]:hover {
                background-color: #e6e6e6;
                border-color: #1677ff;
            }
        """)
        layout.addWidget(button_box)

    def _on_accept(self):
        self.selected_date = self.calendar.selectedDate()
        self.selected_time = QTime(self.hour_spin.value(), self.minute_spin.value())
        self.accept()

# ---------- Левая панель ----------
class LeftPanel(QWidget):
    stocks_updated = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.stocks: List[Tuple[str, str]] = []
        self.selected_tickers: Set[str] = set()
        self.init_ui()
        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor("#1e1e1e"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#1e1e1e"))
        self.setPalette(pal)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 12, 10, 12)
        layout.setSpacing(8)

        title = QLabel("Акции")
        title.setStyleSheet("color: #cccccc; font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        search_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск...")
        self.search_edit.textChanged.connect(self.filter_list)
        search_layout.addWidget(self.search_edit)

        # Кнопка очистки поиска
        self.clear_search_btn = QPushButton("✕")
        self.clear_search_btn.setFixedSize(24, 24)
        self.clear_search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_search_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #aaaaaa;
                border: none;
                font-size: 14px;
                padding: 0px;
            }
            QPushButton:hover {
                color: #ffffff;
                background-color: #3e3e42;
                border-radius: 12px;
            }
        """)
        self.clear_search_btn.clicked.connect(self.search_edit.clear)
        self.clear_search_btn.setVisible(bool(self.search_edit.text()))
        self.search_edit.textChanged.connect(
            lambda text: self.clear_search_btn.setVisible(bool(text))
        )
        search_layout.addWidget(self.clear_search_btn)

        refresh_btn = QPushButton("↻")
        refresh_btn.setFixedWidth(36)
        refresh_btn.clicked.connect(lambda: self.stocks_updated.emit([]))
        search_layout.addWidget(refresh_btn)
        layout.addLayout(search_layout)

        self.list_widget = ToggleListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.list_widget.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list_widget.itemSelectionChanged.connect(self.on_selection_changed)
        layout.addWidget(self.list_widget)

    def load_stocks(self, stocks):
        self.stocks = stocks
        self.update_list()

    def get_sorted_display_stocks(self, filter_text: str = "") -> List[Tuple[str, str]]:
        text = filter_text.lower()
        selected_filtered = []
        unselected_filtered = []
        for name, ticker in self.stocks:
            if text and text not in name.lower() and text not in ticker.lower():
                continue
            if ticker in self.selected_tickers:
                selected_filtered.append((name, ticker))
            else:
                unselected_filtered.append((name, ticker))
        return selected_filtered + unselected_filtered

    def update_list(self, filter_text: str = ""):
        filter_text = self.search_edit.text().lower()
        self.list_widget.blockSignals(True)
        self.list_widget.clear()

        sorted_stocks = self.get_sorted_display_stocks(filter_text)
        for name, ticker in sorted_stocks:
            item = QListWidgetItem(f"{name} - {ticker}")
            item.setData(Qt.ItemDataRole.UserRole, ticker)
            self.list_widget.addItem(item)
            if ticker in self.selected_tickers:
                item.setSelected(True)

        self.list_widget.blockSignals(False)

    def on_selection_changed(self):
        # Все тикеры, которые сейчас отображаются
        visible_tickers = set()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            ticker = item.data(Qt.ItemDataRole.UserRole)
            if ticker:
                visible_tickers.add(ticker)

        # Выбранные среди видимых
        new_selected = set()
        for item in self.list_widget.selectedItems():
            ticker = item.data(Qt.ItemDataRole.UserRole)
            if ticker:
                new_selected.add(ticker)

        # Обновляем глобальный набор: убираем снятые видимые, добавляем выбранные видимые
        self.selected_tickers = (self.selected_tickers - visible_tickers) | new_selected

    def filter_list(self):
        self.update_list()

    def get_selected_tickers(self):
        return list(self.selected_tickers)

    def get_selected_count(self):
        return len(self.selected_tickers)

# ---------- Правая панель ----------
class RightPanel(QWidget):
    download_requested = pyqtSignal(list, str, str, str)

    def __init__(self):
        super().__init__()
        self.folder_path = ""
        self.downloading = False
        self.init_ui()
        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor("#f0f2f5"))
        self.setPalette(pal)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Карточка "Параметры"
        param_card = QFrame()
        param_card.setStyleSheet("background-color: #ffffff; border-radius: 8px; border: none;")
        param_inner = QVBoxLayout(param_card)
        param_inner.setContentsMargins(20, 20, 20, 20)
        param_inner.setSpacing(16)

        param_title = QLabel("Параметры")
        param_title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1e1e1e; border: none;")
        param_inner.addWidget(param_title)

        # Даты
        period_layout = QHBoxLayout()
        period_layout.setSpacing(8)
        lbl_start = QLabel("Начало:")
        lbl_start.setStyleSheet("font-size: 13px; color: #555555;")
        period_layout.addWidget(lbl_start)
        self.start_picker = DateTimePicker()
        self.start_picker.setDateTime(QDateTime(datetime.now().replace(hour=0, minute=0, second=0)))
        period_layout.addWidget(self.start_picker)

        arrow = QLabel("→")
        arrow.setStyleSheet("font-size: 16px; color: #999999; margin: 0 6px;")
        period_layout.addWidget(arrow)

        lbl_end = QLabel("Конец:")
        lbl_end.setStyleSheet("font-size: 13px; color: #555555;")
        period_layout.addWidget(lbl_end)
        self.end_picker = DateTimePicker()
        self.end_picker.setDateTime(QDateTime(datetime.now()))
        period_layout.addWidget(self.end_picker)
        period_layout.addStretch()
        param_inner.addLayout(period_layout)

        # Интервал
        int_layout = QHBoxLayout()
        int_layout.setSpacing(8)
        lbl_int = QLabel("Интервал:")
        lbl_int.setStyleSheet("font-size: 13px; color: #555555;")
        int_layout.addWidget(lbl_int)
        self.interval_combo = QComboBox()
        for code, desc in INTERVALS:
            self.interval_combo.addItem(desc, code)
        self.interval_combo.setCurrentIndex(2)
        self.interval_combo.setStyleSheet("""
            QComboBox {
                background-color: #ffffff;
                color: #1e1e1e;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                padding: 4px 24px 4px 8px;
                font-size: 13px;
                min-width: 100px;
            }
            QComboBox:hover {
                border-color: #1677ff;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border-left: 1px solid #d9d9d9;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                background-color: #f5f5f5;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #1e1e1e;
                selection-background-color: #1677ff;
                selection-color: white;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
            }
        """)
        int_layout.addWidget(self.interval_combo)
        int_layout.addStretch()
        param_inner.addLayout(int_layout)

        # Папка + кнопки
        folder_layout = QHBoxLayout()
        folder_layout.setSpacing(8)
        lbl_folder = QLabel("Папка:")
        lbl_folder.setStyleSheet("font-size: 13px; color: #555555;")
        folder_layout.addWidget(lbl_folder)
        self.folder_label = QLabel(self.folder_path)
        self.folder_label.setStyleSheet(
            "background-color: #fafafa; border: 1px solid #e8e8e8; border-radius: 4px; "
            "padding: 5px 10px; color: #333333; font-size: 13px;"
        )
        self.folder_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        folder_layout.addWidget(self.folder_label)
        browse_btn = QPushButton("Обзор")
        browse_btn.setStyleSheet(
            "QPushButton { background-color: #f5f5f5; color: #333333; border: 1px solid #d9d9d9; "
            "border-radius: 4px; padding: 5px 12px; font-size: 13px; }"
            "QPushButton:hover { border-color: #1677ff; color: #1677ff; }"
        )
        browse_btn.clicked.connect(self.browse_folder)
        folder_layout.addWidget(browse_btn)
        self.download_btn = QPushButton("Скачать")
        self.download_btn.setStyleSheet(
            "QPushButton { background-color: #1677ff; color: white; border: none; "
            "border-radius: 4px; padding: 6px 20px; font-size: 13px; font-weight: 500; }"
            "QPushButton:hover { background-color: #4096ff; }"
            "QPushButton:disabled { background-color: #b0b0b0; }"
        )
        self.download_btn.clicked.connect(self.request_download)
        folder_layout.addWidget(self.download_btn)
        param_inner.addLayout(folder_layout)

        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(
            "QProgressBar { background-color: #f0f0f0; border: none; border-radius: 8px; height: 8px; }"
            "QProgressBar::chunk { background-color: #52c41a; border-radius: 8px; }"
        )
        param_inner.addWidget(self.progress_bar)

        main_layout.addWidget(param_card)

        # Карточка "Логи"
        log_card = QFrame()
        log_card.setStyleSheet("background-color: #ffffff; border-radius: 8px; border: none;")
        log_inner = QVBoxLayout(log_card)
        log_inner.setContentsMargins(20, 20, 20, 20)
        log_inner.setSpacing(8)

        log_title = QLabel("Логи")
        log_title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1e1e1e; border: none;")
        log_inner.addWidget(log_title)

        self.log_list = QListWidget()
        self.log_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.log_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.log_list.setStyleSheet(
            "QListWidget { background-color: #ffffff; border: none; font-size: 13px; color: #333333; }"
            "QListWidget::item { border-bottom: 1px solid #f0f0f0; padding: 6px 4px; }"
            "QListWidget::item:hover { background: transparent; }"
        )
        log_inner.addWidget(self.log_list)

        main_layout.addWidget(log_card, 1)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку", self.folder_path)
        if folder:
            self.set_folder(folder)

    def set_folder(self, path):
        self.folder_path = path
        self.folder_label.setText(path)
        QSettings("moex", "downloader").setValue("last_folder", path)

    def request_download(self):
        self.download_requested.emit([], "", "", "")

    def add_log_entry(self, text: str):
        now = datetime.now().strftime("%H:%M:%S")
        item = QListWidgetItem(f"{now} — {text}")
        item.setFont(QFont("Segoe UI", 10))
        cnt = self.log_list.count()
        if cnt % 2 == 0:
            item.setBackground(QColor("#fafafa"))
        else:
            item.setBackground(QColor("#ffffff"))
        self.log_list.insertItem(0, item)

    def set_downloading(self, state: bool):
        self.downloading = state
        self.download_btn.setEnabled(not state)

    def update_download_button(self, count: int):
        text = f"Скачать ({count})" if count else "Скачать"
        self.download_btn.setText(text)

# ---------- Главное окно ----------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MOEX ISS Скачивание котировок")
        self.setGeometry(100, 100, 950, 650)

        # Иконка окна (отображается на панели задач)
        self.setWindowIcon(QIcon(resource_path("app_icon.ico")))

        self.left_panel = LeftPanel()
        self.right_panel = RightPanel()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.left_panel)
        splitter.addWidget(self.right_panel)
        splitter.setSizes([260, 690])
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background-color: #e0e0e0; }")
        self.setCentralWidget(splitter)

        # Сигналы
        self.left_panel.stocks_updated.connect(self.force_refresh_stocks)
        self.right_panel.download_requested.connect(self.handle_download)
        self.left_panel.list_widget.itemSelectionChanged.connect(
            lambda: self.right_panel.update_download_button(self.left_panel.get_selected_count())
        )

        self.restore_settings()
        self.load_stocks_with_cache()

    def restore_settings(self):
        settings = QSettings("moex", "downloader")
        last_folder = settings.value("last_folder", os.path.expanduser("~"))
        self.right_panel.set_folder(last_folder)

    def load_stocks_with_cache(self):
        cached = load_cached_stocks()
        if cached:
            self.left_panel.load_stocks(cached)
            self.right_panel.add_log_entry(f"Загружено {len(cached)} акций (из кэша)")
        self.refresh_stocks(from_cache=False)

    def force_refresh_stocks(self):
        self.refresh_stocks(from_cache=False)

    def refresh_stocks(self, from_cache=False):
        self.worker = LoadStocksWorker()
        self.worker.finished.connect(self.on_stocks_loaded)
        self.worker.error.connect(lambda e: self.right_panel.add_log_entry(f"Ошибка: {e}"))
        self.worker.start()
        self.right_panel.add_log_entry("Загрузка списка акций...")

    def on_stocks_loaded(self, stocks):
        self.left_panel.load_stocks(stocks)
        save_stocks(stocks)
        self.right_panel.add_log_entry(f"Загружено {len(stocks)} акций (TQBR)")

    def handle_download(self):
        if self.right_panel.downloading:
            QMessageBox.warning(self, "Идёт загрузка", "Дождитесь завершения.")
            return
        tickers = self.left_panel.get_selected_tickers()
        if not tickers:
            QMessageBox.warning(self, "Выберите акции", "Выделите акции в левом списке.")
            return
        start = self.right_panel.start_picker.dateTimeString()
        end = self.right_panel.end_picker.dateTimeString()
        interval = self.right_panel.interval_combo.currentData()
        folder = self.right_panel.folder_path
        if not os.path.isdir(folder):
            QMessageBox.warning(self, "Папка не существует", "Выберите существующую папку.")
            return
        self.right_panel.set_downloading(True)
        self.right_panel.progress_bar.setValue(0)
        self.dl_worker = DownloadWorker(tickers, folder, start, end, interval)
        self.dl_worker.log.connect(self.right_panel.add_log_entry)
        self.dl_worker.progress.connect(self.right_panel.progress_bar.setValue)
        self.dl_worker.finished.connect(self.download_finished)
        self.dl_worker.start()

    def download_finished(self):
        self.right_panel.set_downloading(False)
        self.right_panel.progress_bar.setValue(100)
        self.right_panel.add_log_entry("Все тикеры обработаны")

# ---------- Глобальные стили ----------
GLOBAL_STYLESHEET = """
QWidget#leftPanel {
    background-color: #1e1e1e;
}
QLineEdit {
    background-color: #2d2d30;
    color: #cccccc;
    border: 1px solid #3e3e42;
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 13px;
}
QLineEdit:focus {
    border-color: #1677ff;
}
QListWidget {
    background-color: #1e1e1e;
    color: #cccccc;
    border: none;
    outline: none;
    font-size: 13px;
    padding: 4px;
}
QListWidget::item {
    padding: 6px 12px;
    border-radius: 4px;
    margin: 2px 8px;
}
QListWidget::item:hover {
    background-color: #2a2d2e;
}
QListWidget::item:selected {
    background-color: #1677ff;
    color: white;
}
QScrollBar:vertical {
    background: #1e1e1e;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #3e3e42;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
"""

def main():
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    app.setStyleSheet(GLOBAL_STYLESHEET)
    window = MainWindow()
    window.left_panel.setObjectName("leftPanel")
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()