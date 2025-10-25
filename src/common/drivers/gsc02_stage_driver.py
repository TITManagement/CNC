"""GSC-02 ステージ制御用ドライバ。"""
from __future__ import annotations

import logging
from typing import Dict, Optional, Mapping

from .base import CncDriver
from .gsc02_controller import GSC02

LOG = logging.getLogger(__name__)


class GSC02Driver(CncDriver):
    """GSC-02 コントローラを用いて XY ステージを制御するドライバ。"""

    axes = ("x", "y")
    AXIS_NAMES = {"x": "1", "y": "2"}

    def __init__(
        self,
        port: str,
        *,
        mm_per_pulse: float,
        home_dirs: str = "+-",
        controller_kwargs: Optional[Mapping[str, object]] = None,
        enable_response: bool = True,
    ) -> None:
        """
        Parameters
        ----------
        port:
            シリアルポートパス（例: ``/dev/tty.usbserial-GSC02``）。
        mm_per_pulse:
            1パルスあたりの mm。正の実数である必要があります。
        home_dirs:
            原点復帰時の方向指定。``'+-'`` のように 2 文字で指定します。
        controller_kwargs:
            ``GSC02`` クラスへそのまま渡す追加キーワード。
        """

        if mm_per_pulse is None or mm_per_pulse <= 0:
            raise ValueError("mm_per_pulse は正の数値で指定してください。")
        if not isinstance(home_dirs, str) or len(home_dirs) != 2 or any(c not in "+-" for c in home_dirs):
            raise ValueError("home_dirs は '+-' のように '+' または '-' の2文字で指定してください。")

        kwargs = dict(controller_kwargs or {})
        self._controller = GSC02(port, **kwargs).open()
        self._responses_enabled = bool(enable_response)
        self._controller.set_responses(self._responses_enabled)
        self._mm_per_pulse = float(mm_per_pulse)
        self._home_dirs = home_dirs
        self._positions_pulse: Dict[str, int] = {"x": 0, "y": 0}
        self._default_accel = 100
        self._rapid_speed_mm: Optional[float] = None
        self._cut_speed_mm: Optional[float] = None
        self._current_speed: Optional[int] = None

    # ------------------------------------------------------------------#
    # CncDriver interface
    # ------------------------------------------------------------------#
    def set_units_mm(self) -> None:
        """GSC-02 はパルス単位で動作するため特に処理は行わない。"""

    def set_units_inch(self) -> None:
        """インチ単位への切り替えは未対応のため警告を出す。"""
        LOG.warning("GSC02Driver はインチ単位を直接サポートしていません。")

    def home(self) -> None:
        """両軸の原点復帰を行い、内部位置をゼロリセットする。"""
        self._controller.home("W", self._home_dirs)
        self._controller.go()
        self._positions_pulse = {"x": 0, "y": 0}

    def move_abs(self, *, feed: Optional[float] = None, rapid: bool = False, **axes: float) -> None:
        """絶対座標での移動を相対移動コマンドで実現する。"""
        deltas: Dict[str, int] = {}
        targets: Dict[str, int] = {}
        for logical_axis, mm_value in axes.items():
            if logical_axis not in self.AXIS_NAMES:
                continue
            target = self._convert_mm(mm_value)
            delta = target - self._positions_pulse[logical_axis]
            if delta != 0:
                deltas[logical_axis] = delta
            targets[logical_axis] = target

        if not deltas:
            return

        self._apply_speed(feed, rapid)

        if "x" in deltas and "y" in deltas:
            dirs = "".join("+" if deltas[a] >= 0 else "-" for a in ("x", "y"))
            self._controller.move_rel("W", dirs, abs(deltas["x"]), abs(deltas["y"]))
        else:
            axis = "x" if "x" in deltas else "y"
            axis_code = self.AXIS_NAMES[axis]
            direction = "+" if deltas[axis] >= 0 else "-"
            self._controller.move_rel(axis_code, direction, abs(deltas[axis]))

        self._controller.go()
        for axis, target in targets.items():
            self._positions_pulse[axis] = target

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
            try:
                self._default_accel = int(accel)
            except Exception as exc:
                raise SystemExit(f"accel には整数を指定してください: {accel!r}") from exc
        self._current_speed = None

    def close(self) -> None:
        """シリアルポートをクローズする。"""
        self._controller.close()

    # ------------------------------------------------------------------#
    # Helpers
    # ------------------------------------------------------------------#
    def _apply_speed(self, feed: Optional[float], rapid: bool) -> None:
        target_mm: Optional[float] = None
        if feed is not None:
            target_mm = float(feed)
        elif rapid and self._rapid_speed_mm is not None:
            target_mm = self._rapid_speed_mm
        elif not rapid and self._cut_speed_mm is not None:
            target_mm = self._cut_speed_mm

        if target_mm is None:
            return

        pulses = max(1, self._convert_mm(target_mm))
        if self._current_speed == pulses:
            return

        accel = self._default_accel
        try:
            self._controller.set_speed(
                range_id=1,
                s1=pulses,
                f1=pulses,
                r1=accel,
                s2=pulses,
                f2=pulses,
                r2=accel,
            )
        except Exception as exc:
            LOG.warning("GSC02Driver: 速度設定に失敗しました: %s", exc)
            return

        self._current_speed = pulses

    def _convert_mm(self, value_mm: float) -> int:
        return int(round(value_mm / self._mm_per_pulse))
