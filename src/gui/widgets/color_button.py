from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QColorDialog, QPushButton


class ColorButton(QPushButton):
    colorChanged = Signal(str)

    def __init__(self, color: str = "#ffffff", parent=None) -> None:
        super().__init__(parent)
        self._color = QColor(color)
        if not self._color.isValid():
            self._color = QColor("#ffffff")

        self.clicked.connect(self._choose_color)
        self._refresh()

    def color(self) -> str:
        return self._color.name(QColor.HexRgb)

    def set_color(self, color: str) -> None:
        candidate = QColor(color)
        if not candidate.isValid():
            return

        if candidate == self._color:
            self._refresh()
            return

        self._color = candidate
        self._refresh()
        self.colorChanged.emit(self.color())

    def _choose_color(self) -> None:
        selected = QColorDialog.getColor(
            self._color,
            self,
            "Choose color",
            QColorDialog.ShowAlphaChannel,
        )
        if not selected.isValid():
            return
        self.set_color(selected.name(QColor.HexRgb))

    def _refresh(self) -> None:
        name = self.color()
        lightness = self._color.lightness()
        foreground = "#000000" if lightness > 150 else "#ffffff"
        self.setText(name)
        self.setStyleSheet(
            "QPushButton {"
            f"background:{name}; color:{foreground};"
            "border:1px solid #5f6368; padding:5px 8px;"
            "}"
        )
