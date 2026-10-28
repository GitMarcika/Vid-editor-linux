from typing import Optional

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QWidget

from src.utils.capture_geometry import clamp_rect_to_bounds, fit_aspect_inside


class CaptureFrame(QWidget):
    geometryChanged = Signal(QRect)

    HANDLE_SIZE = 18
    BORDER_WIDTH = 3
    MIN_SIZE = 80

    def __init__(self, parent=None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

        self._screen_bounds = QRect(0, 0, 1920, 1080)
        self._aspect_ratio: Optional[float] = None
        self._resizable = False
        self._drag_mode: Optional[str] = None
        self._drag_start_global = QPoint()
        self._drag_start_geometry = QRect()

        self.resize(640, 360)

    def configure(
        self,
        screen_bounds: QRect,
        width: int,
        height: int,
        aspect_ratio: Optional[float],
        resizable: bool,
        center: bool = True,
    ) -> None:
        self._screen_bounds = QRect(screen_bounds)
        self._aspect_ratio = aspect_ratio
        self._resizable = bool(resizable)

        width = max(1, int(width))
        height = max(1, int(height))

        if self._aspect_ratio is not None:
            width, height = fit_aspect_inside(
                width,
                height,
                self._aspect_ratio,
                self._screen_bounds.width(),
                self._screen_bounds.height(),
                self.MIN_SIZE,
            )

        width = min(width, self._screen_bounds.width())
        height = min(height, self._screen_bounds.height())

        if center:
            x = self._screen_bounds.x() + (
                self._screen_bounds.width() - width
            ) // 2
            y = self._screen_bounds.y() + (
                self._screen_bounds.height() - height
            ) // 2
        else:
            x = self.x()
            y = self.y()

        x, y, width, height = clamp_rect_to_bounds(
            x,
            y,
            width,
            height,
            self._screen_bounds.x(),
            self._screen_bounds.y(),
            self._screen_bounds.width(),
            self._screen_bounds.height(),
        )
        self.setGeometry(x, y, width, height)
        self._emit_geometry()

    def capture_geometry(self) -> QRect:
        return QRect(self.geometry())

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        pen = QPen(QColor("#ff2020"), self.BORDER_WIDTH)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        inset = self.BORDER_WIDTH // 2 + 1
        painter.drawRect(
            inset,
            inset,
            max(1, self.width() - inset * 2 - 1),
            max(1, self.height() - inset * 2 - 1),
        )

        if self._resizable:
            size = self.HANDLE_SIZE
            painter.fillRect(
                self.width() - size,
                self.height() - size,
                size,
                size,
                QColor("#ff2020"),
            )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        self._drag_start_global = event.globalPosition().toPoint()
        self._drag_start_geometry = QRect(self.geometry())

        if self._resizable and self._is_resize_handle(event.position().toPoint()):
            self._drag_mode = "resize"
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            self._drag_mode = "move"
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        local_pos = event.position().toPoint()

        if self._drag_mode is None:
            if self._resizable and self._is_resize_handle(local_pos):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            else:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            super().mouseMoveEvent(event)
            return

        current_global = event.globalPosition().toPoint()
        delta = current_global - self._drag_start_global

        if self._drag_mode == "move":
            self._move_from_drag(delta)
        else:
            self._resize_from_drag(delta)

        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._drag_mode is not None
        ):
            self._drag_mode = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self._emit_geometry()
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            event.accept()
            return
        super().keyPressEvent(event)

    def _move_from_drag(self, delta: QPoint) -> None:
        rect = QRect(self._drag_start_geometry)
        rect.moveTopLeft(rect.topLeft() + delta)

        x, y, width, height = clamp_rect_to_bounds(
            rect.x(),
            rect.y(),
            rect.width(),
            rect.height(),
            self._screen_bounds.x(),
            self._screen_bounds.y(),
            self._screen_bounds.width(),
            self._screen_bounds.height(),
        )
        self.setGeometry(x, y, width, height)
        self._emit_geometry()

    def _resize_from_drag(self, delta: QPoint) -> None:
        start = self._drag_start_geometry
        requested_width = max(
            self.MIN_SIZE,
            start.width() + delta.x(),
        )
        requested_height = max(
            self.MIN_SIZE,
            start.height() + delta.y(),
        )

        max_width = (
            self._screen_bounds.right() - start.x() + 1
        )
        max_height = (
            self._screen_bounds.bottom() - start.y() + 1
        )

        if self._aspect_ratio is not None:
            width, height = fit_aspect_inside(
                requested_width,
                requested_height,
                self._aspect_ratio,
                max_width,
                max_height,
                self.MIN_SIZE,
            )
        else:
            width = min(requested_width, max_width)
            height = min(requested_height, max_height)

        self.setGeometry(
            start.x(),
            start.y(),
            max(1, width),
            max(1, height),
        )
        self._emit_geometry()

    def _is_resize_handle(self, pos: QPoint) -> bool:
        return (
            pos.x() >= self.width() - self.HANDLE_SIZE
            and pos.y() >= self.height() - self.HANDLE_SIZE
        )

    def _emit_geometry(self) -> None:
        self.geometryChanged.emit(QRect(self.geometry()))
