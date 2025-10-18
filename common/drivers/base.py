"""
共通 CNC ドライバインターフェース。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class CncDriver(ABC):
    """
    CNC ドライバの抽象基底クラス。

    G-code インタープリタから呼ばれるメソッド群を明示し、実機/シミュレータ
    双方で一貫した表面を提供する。
    """

    axes: tuple[str, ...] = ()

    @abstractmethod
    def set_units_mm(self) -> None:
        """単位を mm に設定。シミュレータではダミーで構わない。"""

    @abstractmethod
    def set_units_inch(self) -> None:
        """単位を inch に設定。未対応ならダミー実装でよい。"""

    @abstractmethod
    def home(self) -> None:
        """原点復帰処理。"""

    @abstractmethod
    def move_abs(
        self,
        *,
        feed: Optional[float] = None,
        rapid: bool = False,
        **axes: float,
    ) -> None:
        """
        絶対座標へ移動する。

        Parameters
        ----------
        feed:
            送り速度 [mm/min]。未指定の場合は前回値を維持してもよい。
        rapid:
            True の場合は早送り扱い。
        axes:
            軸名（"x", "y", "z" など）とその目標値の組。
        """

    def close(self) -> None:
        """リソース解放が必要なドライバは override する。"""

    def __repr__(self) -> str:  # pragma: no cover - デバッグ用途
        axis_repr = ", ".join(self.axes) if self.axes else "-"
        return f"{self.__class__.__name__}(axes={axis_repr})"
