"""Initial dark desktop theme."""

from PySide6.QtWidgets import QApplication

DARK_STYLESHEET = """
QWidget {
    background-color: #0b111a;
    color: #dce7f3;
    font-family: "Segoe UI";
    font-size: 10pt;
}

QMainWindow {
    background-color: #080d14;
}

QListWidget#navigation {
    background-color: #101925;
    border: 0;
    border-right: 1px solid #233246;
    outline: 0;
    padding: 6px;
}

QListWidget#navigation::item {
    border-radius: 6px;
    color: #aebfd0;
    margin: 2px 4px;
    padding: 10px 12px;
}

QListWidget#navigation::item:hover {
    background-color: #172437;
    color: #ffffff;
}

QListWidget#navigation::item:selected {
    background-color: #173a52;
    border-left: 3px solid #38bdf8;
    color: #ffffff;
}

QLabel#productName {
    color: #ffffff;
    font-size: 15pt;
    font-weight: 700;
}

QLabel#productSubtitle {
    color: #75a4c4;
    font-size: 9pt;
}

QLabel#pageTitle {
    color: #ffffff;
    font-size: 20pt;
    font-weight: 650;
}

QLabel#eyebrow {
    color: #38bdf8;
    font-size: 9pt;
    font-weight: 700;
}

QFrame#card {
    background-color: #101925;
    border: 1px solid #233246;
    border-radius: 10px;
}

QLabel#cardTitle {
    color: #ffffff;
    font-size: 12pt;
    font-weight: 650;
}

QLabel#muted {
    color: #8da1b5;
}

QLabel#statusBadge {
    background-color: #123b32;
    border: 1px solid #1f7a62;
    border-radius: 8px;
    color: #8ff0cf;
    font-weight: 650;
    padding: 6px 10px;
}

QStatusBar {
    background-color: #0d1622;
    border-top: 1px solid #233246;
    color: #8da1b5;
}
"""


def apply_theme(application: QApplication) -> None:
    application.setStyle("Fusion")
    application.setStyleSheet(DARK_STYLESHEET)
