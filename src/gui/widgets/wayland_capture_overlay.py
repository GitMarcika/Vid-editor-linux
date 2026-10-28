from typing import Optional

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen, QScreen
from PySide6.QtWidgets import QWidget

from src.utils.capture_geometry import clamp_rect_to_bounds, fit_aspect_inside


class WaylandCaptureOverlay(QWidget):
    geometryChanged = Signal(QRect)

    HANDLE_SIZE = 22
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
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._target_screen: Optional[QScreen] = None
        self._screen_bounds = QRect(0, 0, 1920, 1080)
        self._selection = QRect(100, 100, 640, 360)
        self._aspect_ratio: Optional[float] = None
        self._resizable = False
        self._drag_mode: Optional[str] = None
        self._drag_start_local = QPoint()
        self._drag_start_selection = QRect()

    def set_target_screen(self, screen: QScreen) -> None:
        self._target_screen = screen

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

        bounds_width = max(1, self._screen_bounds.width())
        bounds_height = max(1, self._screen_bounds.height())

        width = max(1, min(int(width), bounds_width))
        height = max(1, min(int(height), bounds_height))

        if self._aspect_ratio is not None:
            width, height = fit_aspect_inside(
                width,
                height,
                self._aspect_ratio,
                bounds_width,
                bounds_height,
                self.MIN_SIZE,
            )

        if center or not self._selection.isValid():
            x = (bounds_width - width) // 2
            y = (bounds_height - height) // 2
        else:
            x = self._selection.x()
            y = self._selection.y()

        x, y, width, height = clamp_rect_to_bounds(
            x,
            y,
            width,
            height,
            0,
            0,
            bounds_width,
            bounds_height,
        )
        self._selection = QRect(x, y, width, height)
        self.update()
        self._emit_geometry()

    def show_on_screen(self, screen: QScreen) -> None:
        self._target_screen = screen
        handle = self.windowHandle()
        if handle is not None:
            handle.setScreen(screen)

        self.setGeometry(screen.geometry())
        self.showFullScreen()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        self.update()

    def capture_geometry(self) -> QRect:
        return QRect(
            self._screen_bounds.x() + self._selection.x(),
            self._screen_bounds.y() + self._selection.y(),
            self._selection.width(),
            self._selection.height(),
        )

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # Slight dimming outside the selected area makes the region obvious
        # while still leaving the desktop visible for positioning.
        painter.fillRect(self.rect(), QColor(0, 0, 0, 45))

        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_Clear
        )
        painter.fillRect(self._selection, Qt.GlobalColor.transparent)
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_SourceOver
        )

        pen = QPen(QColor("#ff2020"), self.BORDER_WIDTH)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        inset = self.BORDER_WIDTH // 2 + 1
        rect = self._selection.adjusted(inset, inset, -inset, -inset)
        painter.drawRect(rect)

        if self._resizable:
            size = self.HANDLE_SIZE
            painter.fillRect(
                self._selection.right() - size + 1,
                self._selection.bottom() - size + 1,
                size,
                size,
                QColor("#ff2020"),
            )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        pos = event.position().toPoint()
        if not self._selection.contains(pos):
            event.accept()
            return

        self._drag_start_local = pos
        self._drag_start_selection = QRect(self._selection)

        if self._resizable and self._is_resize_handle(pos):
            self._drag_mode = "resize"
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            self._drag_mode = "move"
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pos = event.position().toPoint()

        if self._drag_mode is None:
            if self._resizable and self._is_resize_handle(pos):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif self._selection.contains(pos):
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.unsetCursor()
            super().mouseMoveEvent(event)
            return

        delta = pos - self._drag_start_local
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
        rect = QRect(self._drag_start_selection)
        rect.moveTopLeft(rect.topLeft() + delta)
        x, y, width, height = clamp_rect_to_bounds(
            rect.x(),
            rect.y(),
            rect.width(),
            rect.height(),
            0,
            0,
            self.width(),
            self.height(),
        )
        self._selection = QRect(x, y, width, height)
        self.update()
        self._emit_geometry()

    def _resize_from_drag(self, delta: QPoint) -> None:
        start = self._drag_start_selection
        requested_width = max(
            self.MIN_SIZE,
            start.width() + delta.x(),
        )
        requested_height = max(
            self.MIN_SIZE,
            start.height() + delta.y(),
        )
        max_width = self.width() - start.x()
        max_height = self.height() - start.y()

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

        self._selection = QRect(
            start.x(),
            start.y(),
            max(1, width),
            max(1, height),
        )
        self.update()
        self._emit_geometry()

    def _is_resize_handle(self, pos: QPoint) -> bool:
        if not self._selection.contains(pos):
            return False
        return (
            pos.x() >= self._selection.right() - self.HANDLE_SIZE + 1
            and pos.y() >= self._selection.bottom() - self.HANDLE_SIZE + 1
        )

    def _emit_geometry(self) -> None:
        self.geometryChanged.emit(self.capture_geometry())
