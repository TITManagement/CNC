"""QT-BMM2/QT-BMH2/QT-BMM3 シリアルコマンドヘルパー。

機能仕様（概要）:
    * Central Seiki QT-BMM2 系コントローラが公開している ASCII コマンドセットに対し、
      スレッドセーフなファサード (`QTController`) を提供する。
    * 絶対／相対移動・補間・ジョグ、入出力制御、パラメータアクセス、リセット／非常停止など、
      よく使う操作をメソッドで呼び出せるようにする。
    * シリアル設定や改行コードなどの通信詳細はラッパー内部で扱い、利用側はパルス値等の
      論理的な単位だけを意識すればよい設計とする。
    * 変換処理やレスポンス制御をコンストラクタ引数で差し替えられるようにし、利用者が
      呼び出しコードを編集せずに環境差へ対応できるようにする。

本モジュールのメソッドは公式マニュアルおよび ``docs/QT-BMM2_commands__extracted_.csv`` の
コマンド表を基にしています。実機適用前には、制御対象ファームウェアで動作・単位が一致しているか
必ず確認してください。レスポンスを返さない設定やスケーリングが異なる個体も存在します。
"""
from __future__ import annotations

import threading
from typing import Any, Dict, Optional, Tuple, Union

try:  # pragma: no cover - optional dependency
    import serial  # type: ignore
except Exception as exc:  # pragma: no cover
    serial = None  # type: ignore[misc]


AxisValue = Union[int, float]
AxesPayload = Dict[str, AxisValue]


def _format_axes(axes: AxesPayload) -> str:
    """``A<値> B<値>`` 形式の文字列を生成する（軸は A→B の順）。

    コントローラは軸名を大文字、続いて数値（通常はパルス値）を期待する。
    軸を省略すると、その軸の設定値は変更されない。
    """
    parts = []
    for axis in ("A", "B"):
        if axis in axes and axes[axis] is not None:
            parts.append(f"{axis}{axes[axis]}")
    return " ".join(parts)


class QTController:
    """QT-BMM2 系 ASCII プロトコルのハイレベルラッパー。

    公開メソッドは基本的に仕様書のコマンドと 1:1 に対応する。
    マルチスレッド環境でもコマンドと応答が混線しないよう、内部ロックで排他制御を行う。
    """

    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        timeout: float = 1.0,
        write_timeout: float = 1.0,
        terminator: str = "\r\n",
        encoding: str = "ascii",
        bytesize: int = 8,
        parity: str = "N",
        stopbits: int = 1,
    ) -> None:
        if serial is None:  # pragma: no cover - defensive
            raise RuntimeError("pyserial is required. Please install `pyserial`.")
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.write_timeout = write_timeout
        self.terminator = terminator
        self.encoding = encoding
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits

        self._ser: Optional[serial.Serial] = None  # type: ignore[attr-defined]
        self._lock = threading.Lock()

    # ------------------------------------------------------------------#
    # Context manager helpers
    # ------------------------------------------------------------------#
    def open(self) -> "QTController":
        """シリアルポートを開き、バッファをクリアする。"""
        self._ser = serial.Serial(  # type: ignore[call-arg]
            self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
            write_timeout=self.write_timeout,
            bytesize=self.bytesize,
            parity=self.parity,
            stopbits=self.stopbits,
        )
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()
        return self

    def close(self) -> None:
        """シリアルポートが開いていればフラッシュして閉じる。"""
        if self._ser:
            try:
                self._ser.flush()
            except Exception:
                pass
            self._ser.close()
            self._ser = None

    def __enter__(self) -> "QTController":
        return self.open()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ------------------------------------------------------------------#
    # Low-level IO
    # ------------------------------------------------------------------#
    def _writeln(self, text: str) -> None:
        """コマンド行（末尾の終端文字込み）を書き出す。"""
        if not self._ser:
            raise RuntimeError("Serial port is not open")
        data = (text + self.terminator).encode(self.encoding, errors="ignore")
        self._ser.write(data)
        self._ser.flush()

    def _readline(self) -> str:
        """終端文字またはタイムアウトまで読み取り、文字列に復号する。"""
        if not self._ser:
            raise RuntimeError("Serial port is not open")
        raw = self._ser.readline()
        return raw.decode(self.encoding, errors="ignore").strip()

    def _exchange(self, line: str, expect_reply: Optional[bool] = None) -> Optional[str]:
        """1 行送信し、必要ならレスポンスを待つ。"""
        with self._lock:
            self._writeln(line)
            if expect_reply is False:
                return None
            try:
                reply = self._readline()
                return reply
            except Exception:
                if expect_reply:
                    raise
                return ""

    def _cmd(self, letter: str, payload: str = "", expect_reply: Optional[bool] = None) -> Optional[str]:
        line = f"{letter}:{payload}" if payload else f"{letter}:"
        return self._exchange(line, expect_reply=expect_reply)

    # ------------------------------------------------------------------#
    # Utilities
    # ------------------------------------------------------------------#
    def set_response(self, enable: bool) -> Optional[str]:
        """Toggle controller responses (``X:0`` / ``X:1``)."""
        return self._cmd("X", "1" if enable else "0")

    def ping(self, text: str = "") -> str:
        """Send ``?`` echo. Returns echoed string when responses enabled."""
        return self._cmd("?", text, expect_reply=True) or ""

    def version(self) -> str:
        """Query firmware version (``?`` with empty payload)."""
        return self._cmd("?", "", expect_reply=True) or ""

    # ------------------------------------------------------------------#
    # Motion / I/O helpers
    # ------------------------------------------------------------------#
    def reset(self) -> None:
        """RESET コマンドを送信してコントローラを再初期化する。"""
        self._cmd("RESET", "", expect_reply=False)

    def resta(self) -> None:
        """RESTA コマンドを送信してソフトリスタートする。"""
        self._cmd("RESTA", "", expect_reply=False)

    def estop(self) -> None:
        self._cmd("E", "", expect_reply=False)

    def home(self, *axes: str) -> None:
        if not axes:
            raise ValueError("Specify at least one axis, e.g., 'A' or 'B'")
        payload = " ".join(axes)
        self._cmd("H", payload, expect_reply=False)

    def stop(self, *axes: str) -> None:
        payload = " ".join(axes) if axes else ""
        self._cmd("L", payload, expect_reply=False)

    def wait(self, units_100ms: int) -> None:
        if units_100ms < 0:
            raise ValueError("units_100ms must be >= 0")
        self._cmd("W", f"{units_100ms}", expect_reply=False)

    # -- Speed ---------------------------------------------------------#
    def set_speed(self, axis: str, low: int, high: int, accel: int) -> Optional[str]:
        payload = f"{axis},{low},{high},{accel}"
        return self._cmd("D", payload)

    def read_speed(self, axis: str) -> str:
        return self._cmd("D", f"{axis}R", expect_reply=True) or ""

    # -- Absolute / Relative -------------------------------------------#
    def abs_set(self, **axes: AxisValue) -> None:
        chunk = _format_axes(axes)
        if not chunk:
            raise ValueError("Provide at least one of A=..., B=...")
        self._cmd("A", chunk, expect_reply=False)

    def abs_go(self, **axes: AxisValue) -> None:
        chunk = _format_axes(axes)
        if not chunk:
            raise ValueError("Provide at least one of A=..., B=...")
        self._cmd("AGO", chunk, expect_reply=False)

    def rel_set(self, **axes: AxisValue) -> None:
        chunk = _format_axes(axes)
        if not chunk:
            raise ValueError("Provide at least one of A=..., B=...")
        self._cmd("M", chunk, expect_reply=False)

    def rel_go(self, **axes: AxisValue) -> None:
        chunk = _format_axes(axes)
        if not chunk:
            raise ValueError("Provide at least one of A=..., B=...")
        self._cmd("MGO", chunk, expect_reply=False)

    def go(self, *axes: str) -> None:
        payload = " ".join(axes) if axes else ""
        self._cmd("G", payload, expect_reply=False)

    # -- Linear / Arc --------------------------------------------------#
    def line_set(self, A: AxisValue, B: AxisValue) -> None:
        self._cmd("B", f"A{A} B{B}", expect_reply=False)

    def line_go(self, A: AxisValue, B: AxisValue) -> None:
        self._cmd("BGO", f"A{A} B{B}", expect_reply=False)

    def arc_set(self, Ax: AxisValue, Bx: AxisValue, Ac: AxisValue, Bc: AxisValue, cw_ccw: int) -> None:
        self._cmd("V", f"A{Ax} B{Bx} A{Ac} B{Bc} {cw_ccw}", expect_reply=False)

    def arc_go(self, Ax: AxisValue, Bx: AxisValue, Ac: AxisValue, Bc: AxisValue, cw_ccw: int) -> None:
        self._cmd("VGO", f"A{Ax} B{Bx} A{Ac} B{Bc} {cw_ccw}", expect_reply=False)

    # -- Jog -----------------------------------------------------------#
    def jog(self, **axes_dir: int) -> None:
        chunk = _format_axes(axes_dir)
        if not chunk:
            raise ValueError("Provide A=dir/B=dir")
        self._cmd("J", chunk, expect_reply=False)

    def jog_start(self, **axes_dir: int) -> None:
        chunk = _format_axes(axes_dir)
        if not chunk:
            raise ValueError("Provide A=dir/B=dir")
        self._cmd("JGO", chunk, expect_reply=False)

    # -- IO ------------------------------------------------------------#
    def set_outputs(self, o1: int, o2: int, o3: int, o4: int) -> None:
        self._cmd("C", f"{o4}{o3}{o2}{o1}", expect_reply=False)

    def read_outputs(self) -> str:
        return self._cmd("C", "R", expect_reply=True) or ""

    def read_inputs(self) -> str:
        return self._cmd("Y", "", expect_reply=True) or ""

    def read_sensors(self, axis: Optional[str] = None) -> str:
        payload = axis if axis else ""
        return self._cmd("I", payload, expect_reply=True) or ""

    # -- Parameters / Queries -----------------------------------------#
    def param_read(self, no: int) -> str:
        return self._cmd("P", f"{no}R", expect_reply=True) or ""

    def param_write(self, no: int, *values: Union[int, float, str]) -> None:
        payload = f"{no}" + "".join(str(v) for v in values)
        self._cmd("P", payload, expect_reply=False)

    def query(self, code: int, axis: Optional[str] = None) -> str:
        if axis:
            return self._cmd("Q", f"{axis}{code}", expect_reply=True) or ""
        return self._cmd("Q", f"{code}", expect_reply=True) or ""
