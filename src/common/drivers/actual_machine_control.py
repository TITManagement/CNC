"""実機ドライバ生成用のファクトリモジュール。"""
from __future__ import annotations

import logging
from typing import Any, Callable, Mapping, Optional, Tuple

from .base import CncDriver
from .chuo_stage_driver import ChuoDriver
from .gsc02_stage_driver import GSC02Driver

try:  # pragma: no cover
    import serial  # type: ignore
except Exception:  # pragma: no cover
    serial = None  # type: ignore[misc]

LOG = logging.getLogger(__name__)


def create_actual_driver(driver_name: str, cfg: Mapping[str, Any]) -> Tuple[CncDriver, str]:
    """要求されたドライバ名に応じて実機ドライバを生成する。"""
    if driver_name == "chuo":
        return create_chuo_driver(cfg)
    if driver_name == "gsc02":
        return create_gsc02_driver(cfg)
    raise SystemExit(f"未知のドライバ設定です: {driver_name}")


def create_chuo_driver(cfg: Mapping[str, Any]) -> Tuple[CncDriver, str]:
    """中央精機（QT-BMM2）向けドライバを生成する薄いラッパ。"""
    mm_per_pulse_val, mm_to_device_fn = _parse_mm_per_pulse(cfg)
    driver = _init_chuo_driver(cfg, mm_per_pulse_val, mm_to_device_fn)
    return driver, "chuo"


def create_gsc02_driver(cfg: Mapping[str, Any]) -> Tuple[CncDriver, str]:
    """OptoSigma GSC-02 向けドライバを生成する薄いラッパ。"""
    mm_per_pulse_val, mm_to_device_fn = _parse_mm_per_pulse(cfg)
    driver = _init_gsc02_driver(cfg, mm_per_pulse_val, mm_to_device_fn)
    return driver, "gsc02"


# ---------------------------------------------------------------------------#
# 共通ヘルパ
# ---------------------------------------------------------------------------#
def _parse_mm_per_pulse(
    cfg: Mapping[str, Any],
) -> Tuple[Optional[float], Optional[Callable[[str, float], int]]]:
    mm_per_pulse = cfg.get("mm_per_pulse")
    mm_per_pulse_val: Optional[float] = None
    mm_to_device_fn: Optional[Callable[[str, float], int]] = None

    if callable(mm_per_pulse):
        mm_to_device_fn = mm_per_pulse  # type: ignore[assignment]
    elif mm_per_pulse is not None:
        try:
            mm_per_pulse_val = float(mm_per_pulse)
        except (TypeError, ValueError) as exc:
            raise SystemExit(f"mm_per_pulse は数値で指定してください: {mm_per_pulse!r}") from exc

    return mm_per_pulse_val, mm_to_device_fn


# ---------------------------------------------------------------------------#
# Chuo (QT-BMM2) 用
# ---------------------------------------------------------------------------#
def _init_chuo_driver(
    cfg: Mapping[str, Any],
    mm_per_pulse_val: Optional[float],
    mm_to_device_fn: Optional[Callable[[str, float], int]],
) -> CncDriver:
    kwargs = _build_chuo_kwargs(cfg, mm_per_pulse_val, mm_to_device_fn)
    driver_settings = cfg.get("driver_settings", {})

    try:
        driver = ChuoDriver(**kwargs)
    except Exception as exc:
        if serial is not None and isinstance(exc, serial.SerialException):
            raise SystemExit(f"ChuoDriver: ポート '{kwargs['port']}' を開けませんでした: {exc}") from exc
        raise

    if isinstance(driver_settings, Mapping):
        driver.set_speed_params(
            rapid_speed=driver_settings.get("rapid_speed"),
            cut_speed=driver_settings.get("cut_speed"),
            accel=driver_settings.get("accel"),
        )
    return driver


def _build_chuo_kwargs(
    cfg: Mapping[str, Any],
    mm_per_pulse_val: Optional[float],
    mm_to_device_fn: Optional[Callable[[str, float], int]],
) -> dict[str, Any]:
    port = cfg.get("port")
    if not port:
        raise SystemExit("driver=chuo には port が必要です")

    def _cast_int(value: Any, *, label: str) -> int:
        try:
            return int(value)
        except Exception as exc:
            raise SystemExit(f"{label} には整数値を指定してください: {value!r}") from exc

    def _cast_float(value: Any, *, label: str) -> float:
        try:
            return float(value)
        except Exception as exc:
            raise SystemExit(f"{label} には数値 (float) を指定してください: {value!r}") from exc

    baud = _cast_int(cfg.get("baud", 9600), label="baud")
    timeout = _cast_float(cfg.get("timeout", 1.0), label="timeout")
    write_timeout = _cast_float(cfg.get("write_timeout", 1.0), label="write_timeout")
    accel = _cast_int(cfg.get("qt_accel", cfg.get("accel", 100)), label="qt_accel/accel")
    enable_response = bool(cfg.get("qt_enable_response", True))

    return {
        "port": port,
        "baudrate": baud,
        "timeout": timeout,
        "write_timeout": write_timeout,
        "mm_per_pulse": mm_per_pulse_val,
        "mm_to_device": mm_to_device_fn,
        "default_accel": accel,
        "enable_response": enable_response,
    }


# ---------------------------------------------------------------------------#
# GSC-02 用
# ---------------------------------------------------------------------------#
def _init_gsc02_driver(
    cfg: Mapping[str, Any],
    mm_per_pulse_val: Optional[float],
    mm_to_device_fn: Optional[Callable[[str, float], int]],
) -> CncDriver:
    kwargs = _build_gsc02_kwargs(cfg, mm_per_pulse_val, mm_to_device_fn)
    driver_settings = cfg.get("driver_settings", {})
    try:
        driver = GSC02Driver(**kwargs)
    except Exception as exc:
        if serial is not None and isinstance(exc, serial.SerialException):
            raise SystemExit(f"GSC02Driver: ポート '{kwargs['port']}' を開けませんでした: {exc}") from exc
        raise

    if isinstance(driver_settings, Mapping):
        driver.set_speed_params(
            rapid_speed=driver_settings.get("rapid_speed"),
            cut_speed=driver_settings.get("cut_speed"),
            accel=driver_settings.get("accel"),
        )

    return driver


def _build_gsc02_kwargs(
    cfg: Mapping[str, Any],
    mm_per_pulse_val: Optional[float],
    mm_to_device_fn: Optional[Callable[[str, float], int]],
) -> dict[str, Any]:
    if mm_to_device_fn is not None:
        raise SystemExit("driver=gsc02 では mm_per_pulse に関数を指定できません")
    if mm_per_pulse_val is None:
        raise SystemExit("driver=gsc02 には mm_per_pulse (数値) が必要です")

    port = cfg.get("port")
    if not port:
        raise SystemExit("driver=gsc02 には port が必要です")

    controller_kwargs: dict[str, Any] = {}

    def _optional_cast(key: str, caster: Callable[[Any], Any]) -> None:
        if key in cfg and cfg[key] is not None:
            try:
                controller_kwargs[key] = caster(cfg[key])
            except Exception as exc:
                raise SystemExit(f"{key} の値が不正です: {cfg[key]!r}") from exc

    if cfg.get("baudrate") is not None:
        _optional_cast("baudrate", int)
    elif cfg.get("baud") is not None:
        controller_kwargs["baudrate"] = int(cfg.get("baud"))

    _optional_cast("timeout", float)
    _optional_cast("write_timeout", float)

    for key in ("rtscts", "encoding", "terminator", "bytesize", "parity", "stopbits"):
        if cfg.get(key) is not None:
            controller_kwargs[key] = cfg.get(key)

    home_dirs = cfg.get("gsc_home_dirs", "+-")
    enable_response = bool(cfg.get("gsc_enable_response", True))

    return {
        "port": port,
        "mm_per_pulse": mm_per_pulse_val,
        "home_dirs": str(home_dirs),
        "controller_kwargs": controller_kwargs,
        "enable_response": enable_response,
    }
