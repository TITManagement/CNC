#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Config-driven XY runner
- Drivers: sim / chuo
- Jobs: grid_circles, svg  (NEW: SVG -> path -> moves)
Dependencies:
  pip install pyyaml matplotlib pyserial svgpathtools
"""
import argparse
import logging
import math
import os
import sys
import time
from pathlib import Path
from typing import Mapping, Optional, Any

SRC_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = SRC_DIR.parent
src_str = str(SRC_DIR)
if src_str in sys.path:
    sys.path.remove(src_str)
sys.path.insert(0, src_str)

import matplotlib.pyplot as plt

from common.drivers import CncDriver, create_actual_driver
from common.gcode import LinearGCodeInterpreter, ModalState2D
from common.jobs import Job, JobFactory
from common.platform import EnvironmentAdapter
from common.runtime import ConfigLoader, JobDispatcher, VisualizationController


def _resolve_resource_path(file_entry: str, context: Mapping[str, Any]) -> Path:
    path = Path(file_entry).expanduser()
    if path.is_absolute():
        return path

    # context entries may be Path or str; coerce to str before constructing Path
    config_dir = Path(str(context.get("config_dir", Path.cwd())))
    project_root = Path(str(context.get("project_root", config_dir)))
    candidates = []
    for base in (config_dir, config_dir.parent, project_root):
        if base and base not in candidates:
            candidates.append(base)

    for base in candidates:
        candidate = (base / file_entry).resolve()
        if candidate.exists():
            return candidate
    return (config_dir / file_entry).resolve()


# ========= 共通（簡易Gコードラッパ：直線/円弧） =========
class GCodeWrapper(LinearGCodeInterpreter):
    modal_state_cls = ModalState2D
    linear_axes = ("X", "Y")
    extra_params = ("I", "J")
    motion_g_codes = (0, 1, 2, 3)

    def _handle_extended_motion(self, gcode, params, words):
        if gcode not in (2, 3):
            super()._handle_extended_motion(gcode, params, words)
            return

        cw = gcode == 2
        x_delta = self._unit_to_mm(params["X"]) if "X" in params else None
        y_delta = self._unit_to_mm(params["Y"]) if "Y" in params else None

        if self.m.absolute:
            ex = x_delta if x_delta is not None else self.m.xpos
            ey = y_delta if y_delta is not None else self.m.ypos
        else:
            ex = self.m.xpos + (x_delta if x_delta is not None else 0.0)
            ey = self.m.ypos + (y_delta if y_delta is not None else 0.0)

        i_off = self._unit_to_mm(params.get("I", 0.0))
        j_off = self._unit_to_mm(params.get("J", 0.0))
        cx = self.m.xpos + i_off
        cy = self.m.ypos + j_off

        feed = self._unit_to_mm(params["F"]) if "F" in params else getattr(self.m, "feed", None)

        start = math.atan2(self.m.ypos - cy, self.m.xpos - cx)
        end = math.atan2(ey - cy, ex - cx)
        sweep = end - start
        if cw:
            if sweep >= 0:
                sweep -= 2 * math.pi
        else:
            if sweep <= 0:
                sweep += 2 * math.pi
        radius = math.hypot(self.m.xpos - cx, self.m.ypos - cy)
        e = 0.02
        max_d = 2 * math.acos(max(0.0, 1 - e / max(radius, 1e-9)))
        steps = max(12, int(math.ceil(abs(sweep) / max(1e-3, max_d))))
        logging.debug(
            "[DEBUG] Arc move: ex=%s, ey=%s, cx=%s, cy=%s, R=%s, steps=%s",
            ex,
            ey,
            cx,
            cy,
            radius,
            steps,
        )

        for k in range(1, steps + 1):
            th = start + sweep * (k / steps)
            px = cx + radius * math.cos(th)
            py = cy + radius * math.sin(th)
            logging.debug("[DEBUG] Arc step: px=%s, py=%s, feed=%s", px, py, feed)
            self.drv.move_abs(x=px, y=py, feed=feed, rapid=False)

        self.m.xpos, self.m.ypos = ex, ey


# ========= ドライバ =========
class SimDriver(CncDriver):
    axes = ("x", "y")

    def __init__(self):
        """
        シミュレーション用ドライバ。座標履歴（tracks）を記録し、matplotlibで可視化可能。
        """
        self.tracks = []  # 移動履歴（(x0,y0,x1,y1,rapid,feed)）
        self._cx = 0.0  # 現在のX座標
        self._cy = 0.0  # 現在のY座標

    def set_units_mm(self):
        """
        単位をmmに設定（シミュレーションでは特に処理なし）
        """
        pass

    def set_units_inch(self):
        """
        単位をinchに設定（シミュレーションでは特に処理なし）
        """
        pass

    def home(self):
        """
        原点復帰（座標を0,0にリセット）
        """
        self._cx = self._cy = 0.0

    def move_abs(self, *, feed=None, rapid=False, **axes):
        """指定座標へ移動（履歴に追加）。axes に x/y を与える。"""
        x_val = axes.get("x")
        y_val = axes.get("y")
        nx = self._cx if x_val is None else float(x_val)
        ny = self._cy if y_val is None else float(y_val)
        logging.debug(
            "[DEBUG] SimDriver.move_abs: from=(%s,%s) to=(%s,%s), rapid=%s, feed=%s",
            self._cx,
            self._cy,
            nx,
            ny,
            rapid,
            feed,
        )
        self.tracks.append((self._cx, self._cy, nx, ny, rapid, feed))
        self._cx, self._cy = nx, ny

    def animate_tracks(self, animate=False, fps=2048, title="XY Simulation"):
        """
        移動履歴（tracks）をmatplotlibで可視化
        animate: Trueならアニメーション表示、Falseなら軌跡のみ
        fps: アニメーションのフレームレート
        title: グラフタイトル
        """
        import matplotlib.animation as animation

        if not self.tracks:
            print("No tracks")
            return

        xs = [p for s in self.tracks for p in (s[0], s[2])]
        ys = [p for s in self.tracks for p in (s[1], s[3])]

        xmin, xmax = min(xs), max(xs)
        ymin, ymax = min(ys), max(ys)
        pad = 0.05 * max(xmax - xmin or 1, ymax - ymin or 1)

        fig, ax = plt.subplots()
        ax.set_aspect("equal")
        ax.set_xlim(xmin - pad, xmax + pad)
        ax.set_ylim(ymin - pad, ymax + pad)
        ax.set_xlabel("X [mm]")
        ax.set_ylabel("Y [mm]")
        ax.set_title(title)
        ax.grid(True, linestyle="--", alpha=0.3)
        ax.axhline(0, color="0.6")
        ax.axvline(0, color="0.6")

        if not animate:
            for x0, y0, x1, y1, rapid, _ in self.tracks:
                ax.plot([x0, x1], [y0, y1], ":" if rapid else "-", linewidth=1.2 if rapid else 2.0)
            plt.show()
            return

        lines = []
        for _ in self.tracks:
            (ln,) = ax.plot([], [], "-", lw=2.0)
            lines.append(ln)

        steps = [max(2, 5 + int(math.hypot(s[2] - s[0], s[3] - s[1]) * 2)) for s in self.tracks]

        def data_gen():
            for i, (x0, y0, x1, y1, rapid, _) in enumerate(self.tracks):
                n = steps[i]
                for k in range(1, n + 1):
                    t = k / n
                    yield i, [x0, x0 + (x1 - x0) * t], [y0, y0 + (y1 - y0) * t]

        def init():
            for ln in lines:
                ln.set_data([], [])
            return lines

        def update(fr):
            i, xs_, ys_ = fr
            for j in range(i):
                x0, y0, x1, y1, rapid, _ = self.tracks[j]
                lines[j].set_data([x0, x1], [y0, y1])
                lines[j].set_linestyle(":" if rapid else "-")
            rapid = self.tracks[i][4]
            lines[i].set_data(xs_, ys_)
            lines[i].set_linestyle(":" if rapid else "-")
            return lines

        anim = animation.FuncAnimation(
            fig,
            update,
            frames=data_gen(),
            init_func=init,
            blit=False,
            interval=1000 / fps,
            repeat=False,
            cache_frame_data=False,
        )
        # Keep a reference to the animation to avoid it being garbage-collected
        try:
            fig._anim = anim
        except Exception:
            globals().setdefault("_last_anim", anim)

        plt.show()


# ========= パターン =========
def grid_circles(g, origin, area, cell, circle_d, feed, cw=False, dwell_ms=0, snake=True):
    ox, oy = origin
    W, H = area
    r = circle_d / 2.0
    g.exec("G21 G90")
    g.exec(f"F{feed}")
    nx, ny = int(W // cell), int(H // cell)
    base_cx, base_cy = ox + cell / 2.0, oy + cell / 2.0
    for j in range(ny):
        cols = range(nx) if (not snake or j % 2 == 0) else range(nx - 1, -1, -1)
        for i in cols:
            cx = base_cx + i * cell
            cy = base_cy + j * cell
            logging.debug(f"[DEBUG] grid_circles: center=({cx:.3f},{cy:.3f})")
            g.exec(f"G0 X{cx:.3f} Y{cy:.3f}")
            g.exec(f"G1 X{(cx + r):.3f} Y{cy:.3f}")
            if cw:
                g.exec(f"G2 X{(cx + r):.3f} Y{cy:.3f} I{-r:.3f} J0")
            else:
                g.exec(f"G3 X{(cx + r):.3f} Y{cy:.3f} I{-r:.3f} J0")

            if dwell_ms > 0:
                time.sleep(dwell_ms / 1000.0)


# ---- NEW: SVG → moves ----
def svg_to_moves(
    g,
    file_path,
    origin=(0.0, 0.0),
    px_to_mm=0.264583,
    chord_mm=0.5,
    feed=1200.0,
    y_flip=False,
    svg_height_mm=None,
    sort_paths=False,
):
    """
    file_path: SVGファイルパス（PowerPoint からエクスポートしたもの想定）
    origin: [mm] 左下基準のオフセット
    px_to_mm: ピクセル→mm換算（96dpi基準で ~0.264583 mm/px）
    chord_mm: サンプリング間隔（小さいほど曲線が滑らか、コマンド増）
    feed: 送り [mm/min]
    y_flip: TrueならY軸反転（SVGのYダウン→機械のYアップ）。その際 svg_height_mm が必要。
    svg_height_mm: y_flipする場合の原図の高さ[mm]（viewBox高さ×px_to_mm）
    sort_paths: 左上→右下の順に粗く並べ替え（移動効率を少し改善）
    """
    try:
        from svgpathtools import svg2paths
    except Exception as e:
        raise SystemExit("svgpathtools が必要です: pip install svgpathtools") from e

    if not os.path.exists(file_path):
        raise SystemExit(f"SVG not found: {file_path}")

    paths, attrs = svg2paths(file_path)

    # 粗い並び替え（左上→右下）
    if sort_paths:

        def path_key(p):
            xs = []
            ys = []
            for seg in p:
                for t in (0.0, 0.5, 1.0):
                    z = seg.point(t)
                    xs.append(z.real)
                    ys.append(z.imag)

            return (min(xs), min(ys))

        paths = sorted(paths, key=path_key)

    g.exec("G21 G90")
    g.exec(f"F{feed}")
    ox, oy = origin

    for path in paths:
        # 各セグメントを chord_mm でサンプリング
        pts = []
        for seg in path:
            seg_len_px = max(1e-9, seg.length(error=1e-5))
            seg_len_mm = seg_len_px * px_to_mm
            steps = max(1, int(math.ceil(seg_len_mm / max(1e-6, chord_mm))))
            for k in range(0, steps + 1):
                t = k / steps
                z = seg.point(t)
                x_mm = z.real * px_to_mm
                y_mm = z.imag * px_to_mm
                if y_flip:
                    if svg_height_mm is None:
                        raise SystemExit("y_flip=True の場合は svg_height_mm を指定してください")
                    y_mm = svg_height_mm - y_mm
                pts.append((ox + x_mm, oy + y_mm))
        if not pts:
            continue
        logging.debug(f"[DEBUG] svg_to_moves: path_points={pts}")
        # サブパス開始点へ早送りしてから描画
        sx, sy = pts[0]
        g.exec(f"G0 X{sx:.3f} Y{sy:.3f}")
        for x, y in pts[1:]:
            g.exec(f"G1 X{float(x):.3f} Y{float(y):.3f}")


class GridCirclesJob(Job):
    """グリッド円パターンを描画するジョブ。"""

    def execute(self, *, gcode, context=None):
        defaults = (context or {}).get("defaults", {})
        feed = float(self.config.get("feed", defaults.get("feed", 1200)))
        grid_circles(
            gcode,
            origin=self.config.get("origin", [0, 0]),
            area=self.config.get("area", [100, 100]),
            cell=float(self.config.get("cell", 20)),
            circle_d=float(self.config.get("circle_d", 20)),
            feed=feed,
            cw=bool(self.config.get("cw", False)),
            dwell_ms=int(self.config.get("dwell_ms", 0)),
            snake=bool(self.config.get("snake", True)),
        )


class SvgJob(Job):
    """SVG ファイルのパスをトレースするジョブ。"""

    def execute(self, *, gcode, context=None):
        context = context or {}
        defaults = context.get("defaults", {})
        selector = context.get("select_svg_file")
        Path(context.get("config_dir", Path.cwd()))
        Path(context.get("project_root", Path.cwd()))

        file_entry = self.config.get("file")
        if not file_entry or str(file_entry).strip() == "":
            print("SVGファイルが指定されていません。ファイルを選択してください...")
            if selector:
                selected_path = selector()
            else:
                selected_path = None
            if not selected_path:
                print("SVGファイルが選択されませんでした。スキップします。")
                return
            file_path = Path(selected_path).expanduser()
            print(f"選択されたSVGファイル: {file_path}")
        else:
            file_path = _resolve_resource_path(str(file_entry), context)

        if not file_path.exists():
            print(f"SVGファイル '{file_path}' が見つかりません")
            return

        px_to_mm = float(self.config.get("px_to_mm", 0.264583))
        chord_mm = float(self.config.get("chord_mm", 0.5))
        origin = self.config.get("origin", [0, 0])
        feed = float(self.config.get("feed", defaults.get("feed", 1200)))
        y_flip = bool(self.config.get("y_flip", False))
        svg_height_mm = self.config.get("svg_height_mm")
        if svg_height_mm is not None:
            svg_height_mm = float(svg_height_mm)
        sort_paths = bool(self.config.get("sort_paths", False))
        svg_to_moves(
            gcode,
            file_path=file_path,
            origin=origin,
            px_to_mm=px_to_mm,
            chord_mm=chord_mm,
            feed=feed,
            y_flip=y_flip,
            svg_height_mm=svg_height_mm,
            sort_paths=sort_paths,
        )


def build_xy_job_factory() -> JobFactory:
    factory = JobFactory()
    factory.register("grid_circles", lambda cfg: GridCirclesJob(cfg))
    factory.register("svg", lambda cfg: SvgJob(cfg))
    return factory


class XYRunnerApp:
    """XY ランナーのオーケストレーション。"""

    def __init__(self, args, env: Optional[EnvironmentAdapter] = None):
        self.args = args
        self.env = env or EnvironmentAdapter()
        self._config_loader = ConfigLoader()

    def run(self) -> None:
        config_path_str = self.args.config
        if not config_path_str:
            self._print_usage_examples()
            config_path_str = select_config_interactive()
        config_path = Path(config_path_str)
        cfg = self._config_loader.load(
            str(config_path),
            driver_override=self.args.driver,
        )
        config_dir = config_path.resolve().parent

        driver, driver_name = self._create_driver(cfg)
        g = GCodeWrapper(driver)
        defaults = cfg.get("defaults", {})
        self._apply_defaults(g, defaults)

        factory = build_xy_job_factory()
        dispatcher = JobDispatcher(factory)
        context = {
            "defaults": defaults,
            "select_svg_file": self._select_svg_file,
            "config_dir": config_dir,
            "project_root": ROOT_DIR,
        }
        dispatcher.dispatch_jobs(cfg.get("jobs", []), gcode=g, context=context)

        self._finalize(driver_name, driver, cfg)

    def _print_usage_examples(self) -> None:
        print("\n[Usage :]")
        print("  python src/xy_runner/xy_runner.py --config <設定ファイル.yaml>")
        print("  python src/xy_runner/xy_runner.py --config examples/example_xy/SIM_sample_SVG.yaml")
        print("  python src/xy_runner/xy_runner.py --driver sim --show")
        print("  python src/xy_runner/xy_runner.py --help")
        print("")

    def _create_driver(self, cfg):
        driver_name = self.args.driver or cfg.get("driver", "sim")
        if driver_name == "sim":
            driver = SimDriver()
        else:
            driver, driver_name = create_actual_driver(driver_name, cfg)
        return driver, driver_name

    def _apply_defaults(self, gcode: GCodeWrapper, defaults: dict) -> None:
        if defaults.get("unit", "mm") == "mm":
            gcode.exec("G21")
        else:
            gcode.exec("G20")
        if defaults.get("mode", "absolute") == "absolute":
            gcode.exec("G90")
        else:
            gcode.exec("G91")
        if "feed" in defaults:
            gcode.exec(f"F{float(defaults['feed'])}")

    def _finalize(self, driver_name: str, driver: CncDriver, cfg: dict) -> None:
        vis = cfg.get("visual", {})
        if driver_name == "sim":
            visual = VisualizationController(
                driver,
                default_title="XY Simulation",
                done_message="XY軌跡を表示しました",
                skip_message="軌跡表示をスキップしました（--show または visual.show=true で表示）",
            )
            visual.show(
                cfg_visual=vis,
                force_show=self.args.show,
                disable_animate=self.args.no_animate,
            )
        else:
            if hasattr(driver, "close"):
                driver.close()

    def _select_svg_file(self):
        """GUIでSVGファイルを選択"""
        return self.env.select_file_dialog(
            "SVGファイルを選択してください",
            [("SVG files", "*.svg"), ("All files", "*.*")],
            initialdir=".",
        )


def select_config_interactive():
    import glob

    runner_dir = Path(__file__).resolve().parent
    # Look in multiple locations: current working dir, runner dir, and common examples
    repo_root = runner_dir.parents[1]
    search_dirs = [
        Path.cwd(),
        runner_dir,
        runner_dir / "examples",
        runner_dir / "example",  # legacy layout
        repo_root / "examples",
        repo_root / "examples" / "xy",
        repo_root / "examples" / "example_xy",
    ]

    candidates = []
    for directory in dict.fromkeys(search_dirs):  # preserve order, drop duplicates
        pattern = str(directory / "*.yaml")
        candidates.extend(glob.glob(pattern))

    all_yaml = sorted({Path(f).resolve() for f in candidates})
    if not all_yaml:
        print("YAML設定ファイルが見つかりません。")
        sys.exit(1)
    print("設定ファイルを選択してください:")
    for idx, path in enumerate(all_yaml, 1):
        print(f"  {idx}: {path}")
    while True:
        sel = input("番号を入力してください: ").strip()
        if sel.isdigit() and 1 <= int(sel) <= len(all_yaml):
            chosen = all_yaml[int(sel) - 1]
            print(f": {chosen}")
            return str(chosen)
        print("正しい番号を入力してください。")


# ========= メイン =========
def main():
    # --- コマンドライン引数の解析 ---
    ap = argparse.ArgumentParser(description="Config-driven XY runner (grid/svg)")
    ap.add_argument("--config", help="YAML config path")
    ap.add_argument("--driver", choices=["sim", "chuo"])
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--no-animate", action="store_true")
    ap.add_argument("--debug", action="store_true", help="[DEBUG]出力を有効化")
    args = ap.parse_args()

    # --- ログレベル設定 ---
    import logging

    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")

    app = XYRunnerApp(args)
    app.run()


if __name__ == "__main__":
    main()
