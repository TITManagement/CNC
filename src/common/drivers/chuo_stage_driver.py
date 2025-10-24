"""中央精機ステージを QTController 経由で制御するドライバ。"""
from __future__ import annotations

import logging
from typing import Callable, Dict, Optional

from .base import CncDriver
from .qtbmm2_controller import QTController

LOG = logging.getLogger(__name__)

AxisConverter = Callable[[str, float], int]


class ChuoDriver(CncDriver):
    """QT-BMM2 互換ステージとシリアル通信するドライバ。"""

    axes = ("x", "y")
    AXIS_MAP: Dict[str, str] = {"x": "A", "y": "B"}

    def __init__(
        self,
        port: str,
        *,
        baudrate: int = 9600,
        timeout: float = 1.0,
        write_timeout: float = 1.0,
        mm_per_pulse: Optional[float] = None,
        mm_to_device: Optional[AxisConverter] = None,
        enable_response: bool = True,
        default_accel: int = 100,
    ) -> None:
        """
        パラメータ
        ----------
        port:
            シリアルポートパス。例: ``/dev/ttyUSB0`` や ``COM7``。
        baudrate:
            ボーレート。
        mm_per_pulse:
            ミリ→パルス変換の簡易スケール。指定された場合、``round(mm / mm_per_pulse)`` でパルス生成。
        mm_to_device:
            カスタム変換関数 ``(axis, mm) -> パルス``。指定されていれば ``mm_per_pulse`` より優先。
        enable_response:
            ``X:1`` による応答有効化。ファームによっては有効化しないと応答が返らない。
        default_accel:
            速度設定時に ``D`` コマンドへ渡す加速度パラメータ。
        """

        super().__init__()
        self._controller = QTController(
            port=port,
            baudrate=baudrate,
            timeout=timeout,
            write_timeout=write_timeout,
        ).open()

        if mm_to_device is not None:
            self._mm_to_device = mm_to_device
        elif mm_per_pulse and mm_per_pulse > 0:
            self._mm_to_device = lambda axis, value: int(round(value / mm_per_pulse))
        else:
            self._mm_to_device = lambda axis, value: int(round(value))

        self._default_accel = int(default_accel)
        self._rapid_speed_mm = None  # type: Optional[float]
        self._cut_speed_mm = None  # type: Optional[float]
        self._current_speed = None  # type: Optional[int]

        if enable_response:
            try:
                self._controller.set_response(True)
            except Exception as exc:  # pragma: no cover - depends on device
                LOG.debug("ChuoDriver: failed to enable responses: %s", exc)

    # ------------------------------------------------------------------#
    # Unit handling (noop for now)
    # ------------------------------------------------------------------#
    def set_units_mm(self) -> None:
        """装置はパルス単位で動作するため、ミリ値は内部でパルスに変換される。"""

    def set_units_inch(self) -> None:
        """インチ単位は直接は扱えないためログに警告を出す。"""
        LOG.warning("ChuoDriver does not support inch units; ignoring request.")

    # ------------------------------------------------------------------#
    # Motion commands
    # ------------------------------------------------------------------#
    def home(self) -> None:
        self._controller.home(*self.AXIS_MAP.values())

    def move_abs(self, *, feed: Optional[float] = None, rapid: bool = False, **axes: float) -> None:
        targets = {}
        for logical_axis, value in axes.items():
            if logical_axis not in self.AXIS_MAP:
                continue
            device_axis = self.AXIS_MAP[logical_axis]
            dev_value = self._convert_mm(logical_axis, float(value))
            targets[device_axis] = dev_value

        if not targets:
            return

        self._apply_speed(feed=feed, rapid=rapid)
        LOG.debug("ChuoDriver.move_abs -> targets=%s feed=%s rapid=%s", targets, feed, rapid)
        self._controller.abs_go(**targets)

    def set_speed_params(
        self,
        *,
        rapid_speed: Optional[float] = None,
        cut_speed: Optional[float] = None,
        accel: Optional[int] = None,
    ) -> None:
        if rapid_speed is not None:
            self._rapid_speed_mm = float(rapid_speed)
        if cut_speed is not None:
            self._cut_speed_mm = float(cut_speed)
        if accel is not None:
            self._default_accel = int(accel)
        self._current_speed = None  # force reapply on next move

    def close(self) -> None:
        self._controller.close()

    # ------------------------------------------------------------------#
    # Helpers
    # ------------------------------------------------------------------#
    def _apply_speed(self, *, feed: Optional[float], rapid: bool) -> None:
        mm_per_min = None
        if feed is not None:
            mm_per_min = float(feed)
        elif rapid and self._rapid_speed_mm is not None:
            mm_per_min = self._rapid_speed_mm
        elif not rapid and self._cut_speed_mm is not None:
            mm_per_min = self._cut_speed_mm

        if mm_per_min is None:
            return

        pulses = max(1, self._convert_mm("x", mm_per_min))  # assume same scaling for both axes

        if self._current_speed == pulses:
            return

        for axis in self.AXIS_MAP.values():
            try:
                self._controller.set_speed(axis, pulses, pulses, self._default_accel)
            except Exception as exc:  # pragma: no cover - hardware specific
                LOG.warning("Failed to set speed for axis %s: %s", axis, exc)
        self._current_speed = pulses

    def _convert_mm(self, axis: str, value_mm: float) -> int:
        try:
            converted = self._mm_to_device(axis, value_mm)
        except TypeError:  # backwards compat: mm_to_device(mm) -> value
            converted = self._mm_to_device(value_mm)  # type: ignore[misc]
        return int(round(converted))
