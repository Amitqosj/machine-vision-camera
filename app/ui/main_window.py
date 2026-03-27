"""Main desktop dashboard for real-time inspection control."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import cv2
from PySide6.QtCore import QObject, QRect, Qt, Signal, Slot
from PySide6.QtGui import QCloseEvent, QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.inspection.models import FramePacket, InspectionResult
from app.services.inspection_service import InspectionService
from app.services.report_service import ReportService
from app.ui.log_handler import QtLogHandler
from app.ui.roi_selector import RoiSelectorLabel


class UiSignals(QObject):
    """Cross-thread UI signals from processing threads."""

    frame_ready = Signal(object)
    result_ready = Signal(object)
    status_ready = Signal(dict)
    error_ready = Signal(str)


class MainWindow(QMainWindow):
    """Industrial-style inspection console."""

    def __init__(
        self,
        service: InspectionService,
        report_service: ReportService,
        config_path: Path,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._report_service = report_service
        self._config_path = config_path
        self._signals = UiSignals()
        self._latest_frame_shape: tuple[int, int] | None = None
        self._last_pixmap_rect = QRect()
        self._qt_log_handler = QtLogHandler()

        self._build_ui()
        self._wire_signals()
        self._install_log_handler()

        self._service.set_callbacks(
            on_frame=self._on_frame,
            on_result=self._on_result,
            on_status=self._on_status,
            on_error=self._on_error,
        )
        self._load_settings_to_controls()

    def _build_ui(self) -> None:
        cfg = self._service.config
        self.setWindowTitle(cfg.ui.window_title)
        self.resize(1480, 860)

        root = QWidget(self)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        # Left panel: live preview.
        left_panel = QVBoxLayout()
        self.preview_label = RoiSelectorLabel(self)
        self.preview_label.setFixedSize(cfg.ui.preview_width, cfg.ui.preview_height)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet(
            "background-color: #101010; border: 1px solid #2f2f2f; color: #d0d0d0;"
        )
        self.preview_label.setText("Waiting for camera frames...")
        left_panel.addWidget(self.preview_label)

        # Right panel: controls and telemetry.
        right_panel = QVBoxLayout()
        right_panel.setSpacing(10)

        self.camera_status_label = QLabel("Camera: DISCONNECTED")
        self.camera_status_label.setStyleSheet("font-weight: bold; color: #c03d3d;")

        self.decision_label = QLabel("LAST RESULT: ---")
        self.decision_label.setStyleSheet("font-size: 26px; font-weight: bold; color: #d0d0d0;")

        self.counter_total = QLabel("Total: 0")
        self.counter_pass = QLabel("Pass: 0")
        self.counter_fail = QLabel("Fail: 0")

        counter_row = QHBoxLayout()
        counter_row.addWidget(self.counter_total)
        counter_row.addWidget(self.counter_pass)
        counter_row.addWidget(self.counter_fail)

        right_panel.addWidget(self.camera_status_label)
        right_panel.addWidget(self.decision_label)
        right_panel.addLayout(counter_row)

        button_row = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.capture_btn = QPushButton("Capture Snapshot")
        self.reset_btn = QPushButton("Reset Counters")
        button_row.addWidget(self.start_btn)
        button_row.addWidget(self.stop_btn)
        button_row.addWidget(self.capture_btn)
        button_row.addWidget(self.reset_btn)
        right_panel.addLayout(button_row)

        utility_row = QHBoxLayout()
        self.export_btn = QPushButton("Export CSV")
        self.save_config_btn = QPushButton("Save Config")
        utility_row.addWidget(self.export_btn)
        utility_row.addWidget(self.save_config_btn)
        right_panel.addLayout(utility_row)

        settings_group = QGroupBox("Settings")
        settings_form = QFormLayout(settings_group)

        self.camera_source_input = QLineEdit()
        self.camera_width_input = QSpinBox()
        self.camera_width_input.setRange(320, 4096)
        self.camera_height_input = QSpinBox()
        self.camera_height_input.setRange(240, 2160)
        self.camera_fps_input = QSpinBox()
        self.camera_fps_input.setRange(1, 240)
        self.save_pass_checkbox = QCheckBox("Save PASS images")

        self.roi_enabled_checkbox = QCheckBox("Enable ROI")
        self.roi_x_input = QSpinBox()
        self.roi_y_input = QSpinBox()
        self.roi_w_input = QSpinBox()
        self.roi_h_input = QSpinBox()
        for spin in [self.roi_x_input, self.roi_y_input, self.roi_w_input, self.roi_h_input]:
            spin.setRange(0, 5000)
        self.apply_roi_btn = QPushButton("Apply ROI")

        settings_form.addRow("Camera Source:", self.camera_source_input)
        settings_form.addRow("Width:", self.camera_width_input)
        settings_form.addRow("Height:", self.camera_height_input)
        settings_form.addRow("FPS:", self.camera_fps_input)
        settings_form.addRow(self.save_pass_checkbox)
        settings_form.addRow(self.roi_enabled_checkbox)
        settings_form.addRow("ROI X:", self.roi_x_input)
        settings_form.addRow("ROI Y:", self.roi_y_input)
        settings_form.addRow("ROI Width:", self.roi_w_input)
        settings_form.addRow("ROI Height:", self.roi_h_input)
        settings_form.addRow(self.apply_roi_btn)
        right_panel.addWidget(settings_group)

        recent_fail_group = QGroupBox("Recent Failed Images")
        recent_fail_layout = QVBoxLayout(recent_fail_group)
        self.failed_list = QListWidget()
        self.failed_list.setAlternatingRowColors(True)
        self.failed_list.setMaximumHeight(180)
        recent_fail_layout.addWidget(self.failed_list)
        right_panel.addWidget(recent_fail_group)

        logs_group = QGroupBox("Inspection Logs")
        logs_layout = QVBoxLayout(logs_group)
        self.logs_view = QPlainTextEdit()
        self.logs_view.setReadOnly(True)
        self.logs_view.setMaximumBlockCount(800)
        logs_layout.addWidget(self.logs_view)
        right_panel.addWidget(logs_group)

        root_layout.addLayout(left_panel, stretch=3)
        root_layout.addLayout(right_panel, stretch=2)
        self.setCentralWidget(root)

    def _wire_signals(self) -> None:
        self.preview_label.roi_selected.connect(self._on_roi_dragged)
        self.start_btn.clicked.connect(self._handle_start)
        self.stop_btn.clicked.connect(self._handle_stop)
        self.capture_btn.clicked.connect(self._handle_capture)
        self.reset_btn.clicked.connect(self._handle_reset_counters)
        self.export_btn.clicked.connect(self._handle_export_csv)
        self.save_config_btn.clicked.connect(self._handle_save_config)
        self.apply_roi_btn.clicked.connect(self._apply_roi_from_controls)
        self.failed_list.itemDoubleClicked.connect(self._open_failed_image)

        self._signals.frame_ready.connect(self._render_frame)
        self._signals.result_ready.connect(self._render_result)
        self._signals.status_ready.connect(self._render_status)
        self._signals.error_ready.connect(self._render_error)

    def _install_log_handler(self) -> None:
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        self._qt_log_handler.setFormatter(formatter)
        self._qt_log_handler.setLevel(logging.INFO)
        self._qt_log_handler.emitter.log_message.connect(self._append_log)
        logging.getLogger().addHandler(self._qt_log_handler)

    def _load_settings_to_controls(self) -> None:
        cfg = self._service.config
        self.camera_source_input.setText(str(cfg.camera.source))
        self.camera_width_input.setValue(cfg.camera.width)
        self.camera_height_input.setValue(cfg.camera.height)
        self.camera_fps_input.setValue(cfg.camera.fps)
        self.save_pass_checkbox.setChecked(cfg.inspection.save_pass_images)
        self.roi_enabled_checkbox.setChecked(cfg.inspection.roi.enabled)
        self.roi_x_input.setValue(cfg.inspection.roi.x)
        self.roi_y_input.setValue(cfg.inspection.roi.y)
        self.roi_w_input.setValue(cfg.inspection.roi.width)
        self.roi_h_input.setValue(cfg.inspection.roi.height)

    def _on_frame(self, packet: FramePacket) -> None:
        self._signals.frame_ready.emit(packet)

    def _on_result(self, result: InspectionResult) -> None:
        self._signals.result_ready.emit(result)

    def _on_status(self, snapshot: dict) -> None:
        self._signals.status_ready.emit(snapshot)

    def _on_error(self, message: str) -> None:
        self._signals.error_ready.emit(message)

    @Slot(object)
    def _render_frame(self, packet: FramePacket) -> None:
        frame = packet.frame.copy()
        roi = self._service.config.inspection.roi
        if roi.enabled:
            x, y, w, h = roi.x, roi.y, roi.width, roi.height
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 200, 0), 2)

        self._latest_frame_shape = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        image = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(image).scaled(
            self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.preview_label.setPixmap(pixmap)

        x_off = (self.preview_label.width() - pixmap.width()) // 2
        y_off = (self.preview_label.height() - pixmap.height()) // 2
        self._last_pixmap_rect = QRect(x_off, y_off, pixmap.width(), pixmap.height())

    @Slot(object)
    def _render_result(self, result: InspectionResult) -> None:
        if result.passed:
            self.decision_label.setText("LAST RESULT: PASS")
            self.decision_label.setStyleSheet("font-size: 26px; font-weight: bold; color: #199b4c;")
        else:
            self.decision_label.setText("LAST RESULT: FAIL")
            self.decision_label.setStyleSheet("font-size: 26px; font-weight: bold; color: #cf3333;")

    @Slot(dict)
    def _render_status(self, snapshot: dict) -> None:
        self.counter_total.setText(f"Total: {snapshot.get('total_count', 0)}")
        self.counter_pass.setText(f"Pass: {snapshot.get('pass_count', 0)}")
        self.counter_fail.setText(f"Fail: {snapshot.get('fail_count', 0)}")

        camera_connected = snapshot.get("camera_connected", False)
        if camera_connected:
            self.camera_status_label.setText("Camera: CONNECTED")
            self.camera_status_label.setStyleSheet("font-weight: bold; color: #199b4c;")
        else:
            self.camera_status_label.setText("Camera: DISCONNECTED")
            self.camera_status_label.setStyleSheet("font-weight: bold; color: #c03d3d;")

        self._refresh_failed_list(snapshot.get("recent_failed_images", []))

    @Slot(str)
    def _render_error(self, message: str) -> None:
        self._append_log(f"ERROR | {message}")
        QMessageBox.warning(self, "Inspection Error", message)

    @Slot(str)
    def _append_log(self, message: str) -> None:
        self.logs_view.appendPlainText(message)

    @Slot()
    def _handle_start(self) -> None:
        try:
            self._service.start()
        except Exception as exc:  # pylint: disable=broad-except
            QMessageBox.critical(self, "Start Failed", str(exc))

    @Slot()
    def _handle_stop(self) -> None:
        self._service.stop()

    @Slot()
    def _handle_capture(self) -> None:
        path = self._service.capture_snapshot()
        if path is None:
            QMessageBox.information(self, "Snapshot", "No frame available yet.")
            return
        self._append_log(f"Snapshot saved: {path}")

    @Slot()
    def _handle_reset_counters(self) -> None:
        self._service.reset_counters()

    @Slot()
    def _handle_export_csv(self) -> None:
        path = self._report_service.export_csv()
        self._append_log(f"CSV exported: {path}")
        QMessageBox.information(self, "Export Complete", f"Report saved to:\n{path}")

    @Slot()
    def _handle_save_config(self) -> None:
        cfg = self._service.config
        source = self.camera_source_input.text().strip()
        if source.isdigit():
            cfg.camera.source = int(source)
        else:
            cfg.camera.source = source
        cfg.camera.width = self.camera_width_input.value()
        cfg.camera.height = self.camera_height_input.value()
        cfg.camera.fps = self.camera_fps_input.value()
        cfg.inspection.save_pass_images = self.save_pass_checkbox.isChecked()
        self._apply_roi_from_controls()
        self._service.save_current_config(self._config_path)
        QMessageBox.information(
            self,
            "Configuration Saved",
            "Configuration saved successfully.\nRestart stream to apply camera changes.",
        )

    @Slot()
    def _apply_roi_from_controls(self) -> None:
        enabled = self.roi_enabled_checkbox.isChecked()
        self._service.update_roi(
            x=self.roi_x_input.value(),
            y=self.roi_y_input.value(),
            width=self.roi_w_input.value(),
            height=self.roi_h_input.value(),
            enabled=enabled,
        )

    @Slot(QRect)
    def _on_roi_dragged(self, roi_rect: QRect) -> None:
        if self._latest_frame_shape is None or not self._last_pixmap_rect.isValid():
            return
        frame_h, frame_w = self._latest_frame_shape
        display_rect = roi_rect.intersected(self._last_pixmap_rect)
        if not display_rect.isValid():
            return

        rel_x = display_rect.x() - self._last_pixmap_rect.x()
        rel_y = display_rect.y() - self._last_pixmap_rect.y()
        scale_x = frame_w / max(self._last_pixmap_rect.width(), 1)
        scale_y = frame_h / max(self._last_pixmap_rect.height(), 1)

        x = int(rel_x * scale_x)
        y = int(rel_y * scale_y)
        w = int(display_rect.width() * scale_x)
        h = int(display_rect.height() * scale_y)
        if w <= 0 or h <= 0:
            return

        self.roi_enabled_checkbox.setChecked(True)
        self.roi_x_input.setValue(x)
        self.roi_y_input.setValue(y)
        self.roi_w_input.setValue(w)
        self.roi_h_input.setValue(h)
        self._apply_roi_from_controls()
        self._append_log(f"ROI updated from drag: x={x}, y={y}, w={w}, h={h}")

    @Slot(QListWidgetItem)
    def _open_failed_image(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.UserRole)
        if not path:
            return
        try:
            os.startfile(path)  # type: ignore[attr-defined]
        except Exception as exc:  # pylint: disable=broad-except
            self._append_log(f"Could not open image: {exc}")

    def _refresh_failed_list(self, image_paths: list[str]) -> None:
        self.failed_list.clear()
        for path in image_paths:
            item = QListWidgetItem(Path(path).name)
            item.setData(Qt.UserRole, path)
            self.failed_list.addItem(item)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Ensure clean shutdown."""
        self._service.stop()
        logging.getLogger().removeHandler(self._qt_log_handler)
        super().closeEvent(event)

