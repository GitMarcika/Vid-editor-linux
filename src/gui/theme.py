DARK_STYLESHEET = """
QWidget {
    background-color: #202124;
    color: #e8eaed;
    font-size: 10pt;
}
QMainWindow, QDialog {
    background-color: #202124;
}
QTabWidget::pane {
    border: 1px solid #3c4043;
    background: #202124;
}
QTabBar::tab {
    background: #2b2d30;
    color: #bdc1c6;
    padding: 9px 18px;
    border: 1px solid #3c4043;
    border-bottom: none;
}
QTabBar::tab:selected {
    background: #303134;
    color: #ffffff;
}
QPushButton {
    background: #303134;
    border: 1px solid #5f6368;
    border-radius: 4px;
    padding: 6px 12px;
}
QPushButton:hover {
    background: #3c4043;
}
QPushButton:pressed {
    background: #4a4d51;
}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QListWidget {
    background: #17181a;
    border: 1px solid #5f6368;
    border-radius: 3px;
    padding: 5px;
    selection-background-color: #5f6368;
}
QGroupBox {
    border: 1px solid #3c4043;
    border-radius: 5px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QStatusBar {
    background: #17181a;
    color: #bdc1c6;
}
QSplitter::handle {
    background: #3c4043;
}
QScrollBar:vertical, QScrollBar:horizontal {
    background: #202124;
}
"""
