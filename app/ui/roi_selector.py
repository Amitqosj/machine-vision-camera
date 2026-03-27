"""Interactive ROI selector widget used on top of video preview."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QLabel, QRubberBand


class RoiSelectorLabel(QLabel):
    """Video display label with drag-to-select ROI behavior."""

    roi_selected = Signal(QRect)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._origin = QPoint()
        self._rubber_band = QRubberBand(QRubberBand.Rectangle, self)
        self.setMouseTracking(True)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._origin = event.position().toPoint()
            self._rubber_band.setGeometry(QRect(self._origin, self._origin))
            self._rubber_band.show()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self._origin.isNull():
            rect = QRect(self._origin, event.position().toPoint()).normalized()
            self._rubber_band.setGeometry(rect)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton and self._rubber_band.isVisible():
            rect = self._rubber_band.geometry().normalized()
            self._rubber_band.hide()
            self._origin = QPoint()
            if rect.width() > 8 and rect.height() > 8:
                self.roi_selected.emit(rect)
        super().mouseReleaseEvent(event)

