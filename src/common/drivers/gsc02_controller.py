"""OptoSigma GSC-02 シリアルコマンドヘルパー。

このモジュールは GSC-02 2軸ステージコントローラの ASCII プロトコルを扱う
高レベルラッパーを提供する。設計方針は QTController と揃えており、同様の
コンテキストマネージャ・I/O メソッド構成を採用している。
"""
from __future__ import annotations

import re
import threading
from typing import Any, Dict, Optional

try:  # pragma: no cover - optional dependency
    import serial  # type: ignore
except Exception as exc:  # pragma: no cover
    serial = None  # type: ignore[misc]


class GSC02:
    """OptoSigma GSC-02 ASCII プロトコルの高レベルラッパー。"""

    def __init__(
        self,
        port: str,
        *,
        baudrate: int = 9600,
        timeout: float = 1.0,
        write_timeout: float = 1.0,
        terminator: str = "\r\n",
        encoding: str = "ascii",
        bytesize: int = 8,
        parity: str = "N",
        stopbits: int = 1,
        rtscts: bool = True,
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
        self.rtscts = rtscts

        self._ser: Optional[serial.Serial] = None  # type: ignore[attr-defined]
        self._lock = threading.Lock()
        self._responses_enabled = True

    # ------------------------------------------------------------------#
    # コンテキストマネージャ
    # ------------------------------------------------------------------#
    def open(self) -> "GSC02":
        """シリアルポートを開き、入出力バッファをクリアする。"""
        self._ser = serial.Serial(  # type: ignore[call-arg]
            self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
            write_timeout=self.write_timeout,
            bytesize=self.bytesize,
            parity=self.parity,
            stopbits=self.stopbits,
            rtscts=self.rtscts,
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

    def __enter__(self) -> "GSC02":
        return self.open()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ------------------------------------------------------------------#
    # 低レベル I/O
    # ------------------------------------------------------------------#
    def _writeln(self, text: str) -> None:
        """終端コード付きでコマンド行を送信する。"""
        if not self._ser:
            raise RuntimeError("Serial port is not open")
        data = (text + self.terminator).encode(self.encoding, errors="ignore")
        self._ser.write(data)
        self._ser.flush()

    def _readline(self) -> str:
        """終端まで読み込み、文字列として返す。"""
        if not self._ser:
            raise RuntimeError("Serial port is not open")
        raw = self._ser.readline()
        return raw.decode(self.encoding, errors="ignore").strip()

    def _send(self, line: str, expect_reply: bool = False) -> Optional[str]:
        """コマンドを送信し、必要なら応答を 1 行受信する。"""
        with self._lock:
            self._writeln(line)
            if not expect_reply:
                return None
            if not self._responses_enabled:
                return ""
            try:
                return self._readline()
            except Exception:
                if expect_reply:
                    raise
                return ""

    def set_responses(self, enable: bool) -> None:
        """レスポンス読み取りの有効／無効を切り替える。"""
        self._responses_enabled = bool(enable)

    # ------------------------------------------------------------------#
    # コマンドラッパ
    # ------------------------------------------------------------------#
    def home(self, axes: str, plus_minus: str) -> None:
        """原点復帰 (H:)。軸は '1','2','W' を指定する。"""
        self._validate_axes(axes, plus_minus)
        self._send(f"H:{axes}{plus_minus}", expect_reply=False)

    def move_rel(self, axes: str, dirs: str, pulses1: int, pulses2: Optional[int] = None) -> None:
        """相対移動 (M:)。W 指定時は2軸分のパルスを指定する。"""
        self._validate_axes(axes, dirs)
        if axes in ("1", "2"):
            if pulses1 < 0:
                raise ValueError("pulses must be >= 0")
            self._send(f"M:{axes}{dirs}P{pulses1}", expect_reply=False)
        else:
            if pulses2 is None:
                raise ValueError("pulses2 required for axes='W'")
            if pulses1 < 0 or pulses2 < 0:
                raise ValueError("pulses must be >= 0")
            self._send(f"M:W{dirs[0]}P{pulses1}{dirs[1]}P{pulses2}", expect_reply=False)

    def jog(self, axes: str, dirs: str) -> None:
        """ジョグ移動 (J:)。方向は '+' または '-' で指定する。"""
        self._validate_axes(axes, dirs)
        if axes in ("1", "2"):
            self._send(f"J:{axes}{dirs}", expect_reply=False)
        else:
            self._send(f"J:W{dirs}", expect_reply=False)

    def go(self) -> None:
        """直前の移動設定を実行する G コマンド。"""
        self._send("G", expect_reply=False)

    def stop(self, axis: str = "W", immediate: bool = False) -> None:
        """減速停止 (L:) または即時停止 (L:E)。"""
        if immediate:
            self._send("L:E", expect_reply=False)
            return
        if axis not in ("1", "2", "W"):
            raise ValueError("axis must be '1','2','W'")
        self._send(f"L:{axis}", expect_reply=False)

    def set_logical_origin(self, axis: str = "W") -> None:
        """論理原点を現在値に設定する (R:)。"""
        if axis not in ("1", "2", "W"):
            raise ValueError("axis must be '1','2','W'")
        self._send(f"R:{axis}", expect_reply=False)

    def set_speed(self, range_id: int, s1: int, f1: int, r1: int, s2: int, f2: int, r2: int) -> None:
        """速度テーブル設定 (D:)。range_id は 1 または 2。"""
        if range_id not in (1, 2):
            raise ValueError("range_id must be 1 (Low) or 2 (High)")
        self._send(f"D:{range_id}S{s1}F{f1}R{r1}S{s2}F{f2}R{r2}", expect_reply=False)

    def excite(self, axis: str = "W", on: bool = True) -> None:
        """サーボ励磁制御 (C:)。on=True で励磁、False で解除。"""
        if axis not in ("1", "2", "W"):
            raise ValueError("axis must be '1','2','W'")
        self._send(f"C:{axis}{1 if on else 0}", expect_reply=False)

    # ------------------------------------------------------------------#
    # 状態取得
    # ------------------------------------------------------------------#
    _Q_PATTERN = re.compile(
        r"""^\s*([+\-]?\d{1,10})\s*[,\u3001]\s*([+\-]?\d{1,10})\s*[,\u3001]\s*([A-Z])\s*[,\u3001]\s*([A-Z])\s*[,\u3001]\s*([A-Z])\s*$""",
        re.ASCII,
    )

    def status_raw(self) -> str:
        """Q: の raw 応答文字列を返す。"""
        return self._send("Q:", expect_reply=True) or ""

    def status(self) -> Dict[str, Any]:
        """Q: 応答を辞書化して返す。解析できない場合は raw のみ含める。"""
        raw = self.status_raw()
        match = self._Q_PATTERN.match(raw.replace("、", ","))
        if not match:
            return {"raw": raw}
        pos1, pos2, ack1, ack2, ack3 = match.groups()
        return {
            "pos1": int(pos1),
            "pos2": int(pos2),
            "ack1": ack1,
            "ack2": ack2,
            "ack3": ack3,
            "raw": raw,
        }

    def ready(self) -> bool:
        """!: の応答で Ready (R) か Busy (B) かを判定する。"""
        resp = self._send("!:", expect_reply=True) or ""
        return resp.strip().upper() == "R"

    def version(self) -> str:
        """?:V コマンドでファームウェアバージョンを取得する。"""
        return self._send("?:V", expect_reply=True) or ""

    # ------------------------------------------------------------------#
    # 内部ヘルパ
    # ------------------------------------------------------------------#
    @staticmethod
    def _validate_axes(axes: str, dirs: str) -> None:
        """軸および方向の表記を検証する。"""
        if axes not in ("1", "2", "W"):
            raise ValueError("axes must be '1','2','W'")
        if axes in ("1", "2") and dirs not in ("+", "-"):
            raise ValueError("dirs must be '+' or '-' for single axis")
        if axes == "W":
            if not isinstance(dirs, str) or len(dirs) != 2 or any(c not in "+-" for c in dirs):
                raise ValueError("dirs for axes='W' must be two chars like '+-'")
