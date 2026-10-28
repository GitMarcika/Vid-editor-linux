from typing import Dict, Optional

from PySide6.QtCore import QPointF, QRectF, QSizeF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QMouseEvent,
    QPainter,
    QPen,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtMultimediaWidgets import QGraphicsVideoItem
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
)

from src.utils.overlays import is_text_overlay_active


SCENE_WIDTH = 1280.0
SCENE_HEIGHT = 720.0


class OverlayTextItem(QGraphicsTextItem):
    moved = Signal(str, float, float)
    selectedByUser = Signal(str)
    textEdited = Signal(str, str)

    def __init__(self, overlay_id: str, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.overlay_id = overlay_id
        self._updating_text = False
        self._style_signature = None

        self._background_enabled = False
        self._background_color = QColor("#000000")
        self._background_opacity = 170
        self._background_padding = 8

        self.setFlags(
            QGraphicsTextItem.ItemIsSelectable
            | QGraphicsTextItem.ItemIsMovable
            | QGraphicsTextItem.ItemIsFocusable
            | QGraphicsTextItem.ItemSendsGeometryChanges
        )
        self.setTextInteractionFlags(Qt.NoTextInteraction)

        self.document().contentsChanged.connect(self._on_contents_changed)

    def set_overlay_text(self, text: str) -> None:
        if self.toPlainText() == text:
            return
        self._updating_text = True
        try:
            self.setPlainText(text)
            self._style_signature = None
        finally:
            self._updating_text = False

    def apply_style(self, overlay: Dict[str, object]) -> None:
        signature = (
            str(overlay.get("font_family", "Arial")),
            int(overlay.get("font_size", 28)),
            str(overlay.get("text_color", "#ffffff")),
            bool(overlay.get("background_enabled", False)),
            str(overlay.get("background_color", "#000000")),
            int(overlay.get("background_opacity", 170)),
            int(overlay.get("background_padding", 8)),
            bool(overlay.get("outline_enabled", False)),
            str(overlay.get("outline_color", "#000000")),
            int(overlay.get("outline_width", 2)),
            bool(overlay.get("shadow_enabled", False)),
            str(overlay.get("shadow_color", "#000000")),
            int(overlay.get("shadow_opacity", 160)),
            int(overlay.get("shadow_blur", 8)),
            int(overlay.get("shadow_offset_x", 3)),
            int(overlay.get("shadow_offset_y", 3)),
        )
        if signature == self._style_signature:
            return

        self._style_signature = signature
        self.prepareGeometryChange()
        self._updating_text = True

        font = QFont(str(overlay.get("font_family", "Arial")))
        font.setPointSize(max(6, int(overlay.get("font_size", 28))))
        self.setFont(font)

        text_color = QColor(str(overlay.get("text_color", "#ffffff")))
        if not text_color.isValid():
            text_color = QColor("#ffffff")

        outline_enabled = bool(overlay.get("outline_enabled", False))
        outline_color = QColor(str(overlay.get("outline_color", "#000000")))
        if not outline_color.isValid():
            outline_color = QColor("#000000")
        outline_width = max(0, int(overlay.get("outline_width", 2)))

        char_format = QTextCharFormat()
        char_format.setForeground(text_color)
        if outline_enabled and outline_width > 0:
            char_format.setTextOutline(QPen(outline_color, outline_width))
        else:
            char_format.setTextOutline(QPen(Qt.NoPen))

        cursor = QTextCursor(self.document())
        cursor.select(QTextCursor.Document)
        cursor.mergeCharFormat(char_format)

        self._background_enabled = bool(
            overlay.get("background_enabled", False)
        )
        background_color = QColor(
            str(overlay.get("background_color", "#000000"))
        )
        if not background_color.isValid():
            background_color = QColor("#000000")
        self._background_color = background_color
        self._background_opacity = max(
            0,
            min(255, int(overlay.get("background_opacity", 170))),
        )
        self._background_padding = max(
            0,
            int(overlay.get("background_padding", 8)),
        )

        shadow_enabled = bool(overlay.get("shadow_enabled", False))
        if shadow_enabled:
            shadow_color = QColor(
                str(overlay.get("shadow_color", "#000000"))
            )
            if not shadow_color.isValid():
                shadow_color = QColor("#000000")
            shadow_color.setAlpha(
                max(0, min(255, int(overlay.get("shadow_opacity", 160))))
            )

            effect = QGraphicsDropShadowEffect()
            effect.setColor(shadow_color)
            effect.setBlurRadius(
                max(0.0, float(overlay.get("shadow_blur", 8)))
            )
            effect.setOffset(
                float(overlay.get("shadow_offset_x", 3)),
                float(overlay.get("shadow_offset_y", 3)),
            )
            self.setGraphicsEffect(effect)
        else:
            self.setGraphicsEffect(None)

        self._updating_text = False
        self.update()

    def boundingRect(self) -> QRectF:
        rect = super().boundingRect()
        if self._background_enabled and self._background_padding > 0:
            padding = float(self._background_padding)
            return rect.adjusted(-padding, -padding, padding, padding)
        return rect

    def paint(self, painter: QPainter, option, widget=None) -> None:
        if self._background_enabled:
            color = QColor(self._background_color)
            color.setAlpha(self._background_opacity)
            painter.save()
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            text_rect = super().boundingRect()
            padding = float(self._background_padding)
            background_rect = text_rect.adjusted(
                -padding,
                -padding,
                padding,
                padding,
            )
            radius = max(2.0, min(12.0, padding * 0.65))
            painter.drawRoundedRect(background_rect, radius, radius)
            painter.restore()

        super().paint(painter, option, widget)

    def begin_editing(self) -> None:
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setFocus(Qt.MouseFocusReason)
        cursor = self.textCursor()
        cursor.select(QTextCursor.Document)
        self.setTextCursor(cursor)

    def mousePressEvent(self, event) -> None:
        self.selectedByUser.emit(self.overlay_id)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        super().mouseDoubleClickEvent(event)

    def focusOutEvent(self, event) -> None:
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        super().focusOutEvent(event)

    def itemChange(self, change, value):
        if (
            change == QGraphicsTextItem.ItemPositionChange
            and self.scene() is not None
        ):
            position = QPointF(value)
            scene_rect = self.scene().sceneRect()
            bounds = self.boundingRect()

            min_x = scene_rect.left() - bounds.left()
            min_y = scene_rect.top() - bounds.top()
            max_x = scene_rect.right() - bounds.right()
            max_y = scene_rect.bottom() - bounds.bottom()

            return QPointF(
                min(max(position.x(), min_x), max_x),
                min(max(position.y(), min_y), max_y),
            )

        result = super().itemChange(change, value)

        if (
            change == QGraphicsTextItem.ItemPositionHasChanged
            and self.scene() is not None
        ):
            scene_rect = self.scene().sceneRect()
            if scene_rect.width() > 0 and scene_rect.height() > 0:
                self.moved.emit(
                    self.overlay_id,
                    self.x() / scene_rect.width(),
                    self.y() / scene_rect.height(),
                )

        if (
            change == QGraphicsTextItem.ItemSelectedHasChanged
            and bool(value)
        ):
            self.selectedByUser.emit(self.overlay_id)

        return result

    def _on_contents_changed(self) -> None:
        if self._updating_text:
            return
        self.textEdited.emit(self.overlay_id, self.toPlainText())


class AssemblyPreview(QGraphicsView):
    createTextRequested = Signal(float, float)
    overlayMoved = Signal(str, float, float)
    overlaySelected = Signal(str)
    overlayTextEdited = Signal(str, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._scene = QGraphicsScene(self)
        self._scene.setSceneRect(
            QRectF(0.0, 0.0, SCENE_WIDTH, SCENE_HEIGHT)
        )
        self.setScene(self._scene)

        self.video_item = QGraphicsVideoItem()
        self.video_item.setSize(QSizeF(SCENE_WIDTH, SCENE_HEIGHT))
        self.video_item.setAspectRatioMode(Qt.KeepAspectRatio)
        self.video_item.setZValue(0)
        self._scene.addItem(self.video_item)

        self._overlay_items: Dict[str, OverlayTextItem] = {}
        self._current_time_ms = 0

        self.setBackgroundBrush(QColor("#0f1011"))
        self.setFrameShape(QFrame.NoFrame)
        self.setMinimumHeight(360)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        item = self.itemAt(event.position().toPoint())
        if (
            event.button() == Qt.LeftButton
            and (item is None or item is self.video_item)
        ):
            scene_pos = self.mapToScene(event.position().toPoint())
            rect = self._scene.sceneRect()
            if rect.contains(scene_pos):
                x_norm = (
                    scene_pos.x() - rect.left()
                ) / rect.width()
                y_norm = (
                    scene_pos.y() - rect.top()
                ) / rect.height()
                self.createTextRequested.emit(x_norm, y_norm)
                event.accept()
                return

        super().mousePressEvent(event)

    def sync_overlays(
        self,
        overlays,
        current_time_ms: Optional[int] = None,
    ) -> None:
        if current_time_ms is not None:
            self._current_time_ms = max(0, int(current_time_ms))

        incoming_ids = {
            str(item.get("id"))
            for item in overlays
            if item.get("id")
        }

        for overlay_id in list(self._overlay_items):
            if overlay_id not in incoming_ids:
                item = self._overlay_items.pop(overlay_id)
                self._scene.removeItem(item)

        rect = self._scene.sceneRect()

        for overlay in overlays:
            overlay_id = str(overlay.get("id", ""))
            if not overlay_id:
                continue

            item = self._overlay_items.get(overlay_id)
            if item is None:
                item = OverlayTextItem(
                    overlay_id,
                    str(overlay.get("text", "Text")),
                )
                item.setZValue(10)
                item.moved.connect(self.overlayMoved)
                item.selectedByUser.connect(self.overlaySelected)
                item.textEdited.connect(self.overlayTextEdited)
                self._scene.addItem(item)
                self._overlay_items[overlay_id] = item

            item.set_overlay_text(str(overlay.get("text", "Text")))
            item.apply_style(overlay)

            x_norm = min(
                1.0,
                max(0.0, float(overlay.get("x_norm", 0.5))),
            )
            y_norm = min(
                1.0,
                max(0.0, float(overlay.get("y_norm", 0.5))),
            )
            desired = QPointF(
                rect.left() + x_norm * rect.width(),
                rect.top() + y_norm * rect.height(),
            )
            if (item.pos() - desired).manhattanLength() > 0.5:
                item.blockSignals(True)
                item.setPos(desired)
                item.blockSignals(False)

            item.setVisible(
                is_text_overlay_active(
                    overlay,
                    self._current_time_ms,
                )
            )

    def set_current_time(self, global_time_ms: int, overlays) -> None:
        self.sync_overlays(overlays, global_time_ms)

    def select_overlay(self, overlay_id: str) -> None:
        item = self._overlay_items.get(overlay_id)
        if item is None:
            return

        self._scene.clearSelection()
        item.setSelected(True)
        self.centerOn(item)

    def begin_editing_overlay(self, overlay_id: str) -> None:
        item = self._overlay_items.get(overlay_id)
        if item is None:
            return
        self.select_overlay(overlay_id)
        item.begin_editing()
