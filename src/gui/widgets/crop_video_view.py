from typing import Optional, Tuple

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QWidget

from src.utils.geometry import clamp_crop_origin, fitted_rect


class CropOverlay(QWidget):
    cropChanged = Signal(int, int, int, int)
    validityChanged = Signal(bool, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

        self._video_size = QSize()
        self._crop_width = 1920
        self._crop_height = 1080
        self._crop_x = 0
        self._crop_y = 0
        self._dragging = False
        self._last_mouse_pos = QPoint()
        self._last_validity: Optional[Tuple[bool, str]] = None
        self._explicit_crop_position = False

    def set_video_size(self, size: QSize) -> None:
        old_size = self._video_size
        self._video_size = QSize(size)

        if self._video_size.isValid():
            if not old_size.isValid() and not self._explicit_crop_position:
                self._center_crop()
            else:
                self._crop_x, self._crop_y = clamp_crop_origin(
                    self._crop_x,
                    self._crop_y,
                    self._crop_width,
                    self._crop_height,
                    self._video_size.width(),
                    self._video_size.height(),
                )

        self._emit_state()
        self.update()

    def set_crop_size(self, width: int, height: int) -> None:
        old_width = self._crop_width
        old_height = self._crop_height
        self._crop_width = max(1, int(width))
        self._crop_height = max(1, int(height))

        if self._video_size.isValid():
            center_x = self._crop_x + old_width / 2.0
            center_y = self._crop_y + old_height / 2.0
            self._crop_x = round(center_x - self._crop_width / 2.0)
            self._crop_y = round(center_y - self._crop_height / 2.0)
            self._crop_x, self._crop_y = clamp_crop_origin(
                self._crop_x,
                self._crop_y,
                self._crop_width,
                self._crop_height,
                self._video_size.width(),
                self._video_size.height(),
            )

        self._emit_state()
        self.update()

    def set_crop_rect(self, x: int, y: int, width: int, height: int) -> None:
        self._crop_x = max(0, int(x))
        self._crop_y = max(0, int(y))
        self._crop_width = max(1, int(width))
        self._crop_height = max(1, int(height))
        self._explicit_crop_position = True

        if self._video_size.isValid():
            self._crop_x, self._crop_y = clamp_crop_origin(
                self._crop_x,
                self._crop_y,
                self._crop_width,
                self._crop_height,
                self._video_size.width(),
                self._video_size.height(),
            )

        self._emit_state()
        self.update()

    def reset_for_new_video(self) -> None:
        self._explicit_crop_position = False
        self._video_size = QSize()
        self._crop_x = 0
        self._crop_y = 0
        self._emit_state()
        self.update()

    def crop_rect_source(self) -> Tuple[int, int, int, int]:
        return (
            self._crop_x,
            self._crop_y,
            self._crop_width,
            self._crop_height,
        )

    def is_crop_valid(self) -> bool:
        if not self._video_size.isValid():
            return False
        return (
            self._crop_width <= self._video_size.width()
            and self._crop_height <= self._video_size.height()
        )

    def validation_message(self) -> str:
        if not self._video_size.isValid():
            return "Waiting for video dimensions."
        if self._crop_width > self._video_size.width():
            return (
                f"Crop width {self._crop_width}px exceeds video width "
                f"{self._video_size.width()}px."
            )
        if self._crop_height > self._video_size.height():
            return (
                f"Crop height {self._crop_height}px exceeds video height "
                f"{self._video_size.height()}px."
            )
        return ""

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        video_rect = self._displayed_video_rect()
        if video_rect.isEmpty():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        crop_rect = self._displayed_crop_rect()
        if crop_rect is None:
            painter.setPen(QPen(QColor(220, 80, 80), 2))
            painter.drawRect(video_rect)
            return

        shade = QColor(0, 0, 0, 105)
        painter.fillRect(
            QRectF(
                video_rect.left(),
                video_rect.top(),
                video_rect.width(),
                max(0.0, crop_rect.top() - video_rect.top()),
            ),
            shade,
        )
        painter.fillRect(
            QRectF(
                video_rect.left(),
                crop_rect.bottom(),
                video_rect.width(),
                max(0.0, video_rect.bottom() - crop_rect.bottom()),
            ),
            shade,
        )
        painter.fillRect(
            QRectF(
                video_rect.left(),
                crop_rect.top(),
                max(0.0, crop_rect.left() - video_rect.left()),
                crop_rect.height(),
            ),
            shade,
        )
        painter.fillRect(
            QRectF(
                crop_rect.right(),
                crop_rect.top(),
                max(0.0, video_rect.right() - crop_rect.right()),
                crop_rect.height(),
            ),
            shade,
        )

        painter.setPen(QPen(QColor(255, 193, 7), 2))
        painter.drawRect(crop_rect)

        center = crop_rect.center()
        painter.drawLine(
            int(center.x() - 8),
            int(center.y()),
            int(center.x() + 8),
            int(center.y()),
        )
        painter.drawLine(
            int(center.x()),
            int(center.y() - 8),
            int(center.x()),
            int(center.y() + 8),
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            crop_rect = self._displayed_crop_rect()
            if crop_rect is not None and crop_rect.contains(event.position()):
                self._dragging = True
                self._last_mouse_pos = event.position().toPoint()
                self.setCursor(Qt.ClosedHandCursor)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        crop_rect = self._displayed_crop_rect()

        if self._dragging:
            video_rect = self._displayed_video_rect()
            if video_rect.width() <= 0 or self._video_size.width() <= 0:
                return

            current = event.position().toPoint()
            delta = current - self._last_mouse_pos
            self._last_mouse_pos = current

            source_per_display = self._video_size.width() / video_rect.width()
            source_dx = round(delta.x() * source_per_display)
            source_dy = round(delta.y() * source_per_display)

            self._crop_x, self._crop_y = clamp_crop_origin(
                self._crop_x + source_dx,
                self._crop_y + source_dy,
                self._crop_width,
                self._crop_height,
                self._video_size.width(),
                self._video_size.height(),
            )
            self._explicit_crop_position = True
            self._emit_state()
            self.update()
            event.accept()
            return

        if crop_rect is not None and crop_rect.contains(event.position()):
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.unsetCursor()

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            self.setCursor(Qt.OpenHandCursor)
            self._emit_state()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event) -> None:
        if not self._dragging:
            self.unsetCursor()
        super().leaveEvent(event)

    def _center_crop(self) -> None:
        if not self._video_size.isValid():
            return
        self._crop_x = max(
            0,
            (self._video_size.width() - self._crop_width) // 2,
        )
        self._crop_y = max(
            0,
            (self._video_size.height() - self._crop_height) // 2,
        )
        self._crop_x, self._crop_y = clamp_crop_origin(
            self._crop_x,
            self._crop_y,
            self._crop_width,
            self._crop_height,
            self._video_size.width(),
            self._video_size.height(),
        )

    def _displayed_video_rect(self) -> QRectF:
        rect = fitted_rect(
            float(self.width()),
            float(self.height()),
            float(self._video_size.width()),
            float(self._video_size.height()),
        )
        return QRectF(rect.x, rect.y, rect.width, rect.height)

    def _displayed_crop_rect(self) -> Optional[QRectF]:
        if not self.is_crop_valid():
            return None

        video_rect = self._displayed_video_rect()
        if video_rect.isEmpty():
            return None

        scale = video_rect.width() / self._video_size.width()
        return QRectF(
            video_rect.x() + self._crop_x * scale,
            video_rect.y() + self._crop_y * scale,
            self._crop_width * scale,
            self._crop_height * scale,
        )

    def _emit_state(self) -> None:
        valid = self.is_crop_valid()
        message = self.validation_message()
        state = (valid, message)

        if state != self._last_validity:
            self._last_validity = state
            self.validityChanged.emit(valid, message)

        self.cropChanged.emit(
            self._crop_x,
            self._crop_y,
            self._crop_width,
            self._crop_height,
        )


class CropVideoView(QWidget):
    cropChanged = Signal(int, int, int, int)
    validityChanged = Signal(bool, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(360)

        self.video_widget = QVideoWidget(self)
        self.video_widget.setAspectRatioMode(Qt.KeepAspectRatio)
        self.video_widget.setStyleSheet("background:#0f1011;")

        self.overlay = CropOverlay(self)
        self.overlay.cropChanged.connect(self.cropChanged)
        self.overlay.validityChanged.connect(self.validityChanged)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.video_widget.setGeometry(self.rect())
        self.overlay.setGeometry(self.rect())
        self.overlay.raise_()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.overlay.raise_()

    def set_video_size(self, size: QSize) -> None:
        self.overlay.set_video_size(size)

    def set_crop_size(self, width: int, height: int) -> None:
        self.overlay.set_crop_size(width, height)

    def set_crop_rect(self, x: int, y: int, width: int, height: int) -> None:
        self.overlay.set_crop_rect(x, y, width, height)

    def reset_for_new_video(self) -> None:
        self.overlay.reset_for_new_video()

    def crop_rect_source(self) -> Tuple[int, int, int, int]:
        return self.overlay.crop_rect_source()

    def is_crop_valid(self) -> bool:
        return self.overlay.is_crop_valid()
