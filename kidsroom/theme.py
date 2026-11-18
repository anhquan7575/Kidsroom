from PySide6.QtCore import QTranslator
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


class VietnameseButtons(QTranslator):
    def translate(self, context, sourceText, disambiguation=None, n=-1):
        if context in {"QPlatformTheme", "QDialogButtonBox", "QMessageBox"}:
            return {
                "OK": "Đồng ý", "&OK": "Đồng ý",
                "Save": "Lưu", "&Save": "Lưu",
                "Cancel": "Hủy", "&Cancel": "Hủy",
                "Yes": "Có", "&Yes": "Có",
                "No": "Không", "&No": "Không",
                "Close": "Đóng", "&Close": "Đóng",
            }.get(sourceText, "")
        return ""


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    palette = QPalette()
    colors = {
        QPalette.ColorRole.Window: "#101522",
        QPalette.ColorRole.WindowText: "#edf2ff",
        QPalette.ColorRole.Base: "#151d2e",
        QPalette.ColorRole.AlternateBase: "#1c263b",
        QPalette.ColorRole.Text: "#edf2ff",
        QPalette.ColorRole.Button: "#25324b",
        QPalette.ColorRole.ButtonText: "#edf2ff",
        QPalette.ColorRole.Highlight: "#6054cf",
        QPalette.ColorRole.HighlightedText: "#ffffff",
        QPalette.ColorRole.ToolTipBase: "#25324b",
        QPalette.ColorRole.ToolTipText: "#edf2ff",
        QPalette.ColorRole.PlaceholderText: "#9aa9c3",
        QPalette.ColorRole.Link: "#a7bdff",
    }
    for role, color in colors.items():
        palette.setColor(role, QColor(color))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText,
                 QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor("#8390a6"))
    app.setPalette(palette)
    app.vietnamese_buttons = VietnameseButtons(app)
    app.installTranslator(app.vietnamese_buttons)
    app.setStyleSheet("""
        QWidget { font-family: "Segoe UI"; font-size: 14px; color: #edf2ff; }
        QMainWindow, QDialog, QWidget#learningPage { background: #101522; }
        QLabel { background: transparent; }
        QLabel#heading { font-size: 32px; font-weight: 700; color: #f3f5ff; }
        QLabel#eyebrow { color: #b6aaff; font-size: 13px; font-weight: 700; }
        QLabel#subtitle, QLabel#hint { color: #b7c4da; }
        QLabel#sectionTitle { font-size: 19px; font-weight: 600; }
        QLabel#rewardSummary {
            background: #1c3041; color: #a4f0db; border: 1px solid #305764;
            border-radius: 12px; padding: 14px; font-weight: 600;
        }
        QWidget#hero {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #262345, stop:1 #183345);
            border: 1px solid #3b4264; border-radius: 20px;
        }
        QFrame#questionCard {
            background: #1a2437; border: 1px solid #33425c; border-radius: 14px;
        }
        QPushButton {
            background: #25324b; border: 1px solid #435371;
            border-radius: 9px; padding: 10px 14px; font-weight: 600;
        }
        QPushButton:hover { background: #334361; border-color: #9cafff; }
        QPushButton:pressed { background: #1e2940; }
        QPushButton:focus { border: 2px solid #bdcaff; }
        QPushButton#primary {
            background: #6656d9; border-color: #8d7eec; color: white;
        }
        QPushButton#primary:hover { background: #7967ec; }
        QPushButton#danger { color: #ffbccb; border-color: #855064; }
        QPushButton:disabled {
            background: #1b2435; border-color: #303c50; color: #8390a6;
        }
        QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
            background: #151d2e; border: 1px solid #465572;
            border-radius: 7px; padding: 8px; selection-background-color: #6054cf;
        }
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus,
        QSpinBox:focus, QDoubleSpinBox:focus { border-color: #b4a5ff; }
        QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled,
        QSpinBox:disabled, QDoubleSpinBox:disabled { color: #8390a6; background: #1b2435; }
        QComboBox QAbstractItemView { background: #1c263b; selection-background-color: #6054cf; }
        QListWidget {
            background: #151d2e; border: 1px solid #33425c;
            border-radius: 14px; padding: 8px; outline: 0;
        }
        QListWidget::item { padding: 13px; margin: 3px; border-radius: 8px; }
        QListWidget::item:hover { background: #26344c; }
        QListWidget::item:selected { background: #383660; color: #ffffff; }
        QListWidget::item:focus { border: 1px solid #b4a5ff; }
        QListWidget#missions::item { padding: 18px; font-size: 16px; }
        QTableWidget {
            background: #151d2e; border: 1px solid #33425c;
            border-radius: 10px; gridline-color: #33425c;
            outline: 0; color: #edf2ff;
        }
        QTableWidget::item {
            padding: 8px 10px;
            border-bottom: 1px solid #33425c;
            border-right: 1px solid #33425c;
        }
        QTableWidget::item:hover { background: #212c42; }
        QTableWidget::item:selected { background: #383660; color: #ffffff; }
        QHeaderView::section {
            background: #1c263b; color: #b7c4da;
            padding: 8px 10px; font-weight: 700;
            border: 1px solid #33425c;
        }
        QTabWidget::pane { border: 1px solid #33425c; border-radius: 10px; padding: 10px; }
        QTabBar::tab {
            background: #1b2435; color: #b7c4da; padding: 12px 16px;
            border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 4px;
        }
        QTabBar::tab:selected { background: #383660; color: #ffffff; }
        QTabBar::tab:hover { background: #2a3550; }
        QScrollArea { border: none; background: transparent; }
        QScrollBar:vertical { background: #151d2e; width: 12px; margin: 0; }
        QScrollBar::handle:vertical { background: #526282; min-height: 28px; border-radius: 5px; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        QCheckBox { spacing: 9px; padding: 5px 0; }
        QCheckBox::indicator {
            width: 18px; height: 18px; border: 1px solid #8494b3;
            border-radius: 4px; background: #151d2e;
        }
        QCheckBox::indicator:checked { background: #a698ff; border: 3px solid #4d428a; }
        QMenu { background: #1c263b; border: 1px solid #465572; padding: 5px; }
        QMenu::item { padding: 9px 22px; }
        QMenu::item:selected { background: #383660; }
        QToolTip { background: #25324b; color: #edf2ff; border: 1px solid #8494b3; }
    """)
