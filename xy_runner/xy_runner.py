#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Config-driven XY runner
- Drivers: sim / chuo
- Jobs: grid_circles, svg  (NEW: SVG -> path -> moves) 
Dependencies:
  pip install pyyaml matplotlib pyserial svgpathtools
"""
import math, re, time, argparse, yaml, os, sys
from dataclasses import dataclass
import threading
import queue
import matplotlib.pyplot as plt
import time
import logging

# ========= 共通（簡易Gコードラッパ：直線/円弧） =========
@dataclass
class ModalState:
    units_mm: bool = True
    absolute: bool = True
    feed: float = 1200.0
    xpos: float = 0.0
    ypos: float = 0.0

class GCodeWrapper:
    def __init__(self, driver):
        """
        ドライバ（SimDriver/ChuoDriver）を受け取り、Gコード状態管理を初期化
        driver: CNC動作を実行するドライバインスタンス
        """
        self.drv = driver
        self.m = ModalState()

    def exec(self, line: str):
        """
        1行のGコードコマンドを解釈し、ドライバに動作指示を出す
        line: Gコード文字列（例: "G1 X10 Y20 F1200"）
        - モーダルコマンド（単位・座標モード・送り速度）を状態に反映
        - 動作コマンド（G0,G1,G2,G3）は _motion() で処理
        """
        logging.debug(f"[DEBUG] GCodeWrapper.exec: line='{line}'")
        line = self._strip_comment(line).strip()
        if not line: return
        if line.startswith("$H"): self.drv.home(); return
        words = re.findall(r'[A-Za-z][+\-0-9\.]*', line)
        # モーダル
        for w in words:
            c,v=w[0].upper(),w[1:]
            if c=='G':
                g=float(v)
                if g==20: self.m.units_mm=False; self.drv.set_units_inch()
                if g==21: self.m.units_mm=True;  self.drv.set_units_mm()
                if g==90: self.m.absolute=True
                if g==91: self.m.absolute=False
        for w in words:
            if w[0].upper()=='F': self.m.feed=float(w[1:])
        # 動作
        if any(w.upper().startswith(t) for w in words for t in ('G0','G1','G2','G3')):
            self._motion(words)

    def _unit_to_mm(self, v):
        """
        単位変換: mmモードならそのまま、inchモードならmmへ変換
        v: 値（mmまたはinch）
        return: mm単位の値
        """
        return v if self.m.units_mm else v*25.4

    def _motion(self, words):
        """
        動作コマンド（G0,G1,G2,G3）を解釈し、直線/円弧移動をドライバに指示
        words: コマンド分割済みリスト
        - G0/G1: 直線移動（X,Y座標、F送り速度）
        - G2/G3: 円弧移動（X,Y終点, I,J中心, F送り速度, CW/CCW）
        """
        gcode, prm = None, {}
        for w in words:
            c,v=w[0].upper(),w[1:]
            if c=='G': gcode=int(float(v))
            elif c in ('X','Y','I','J','F'): prm[c]=float(v)
        if gcode in (0,1):
            x = self._unit_to_mm(prm['X']) if 'X' in prm else None
            y = self._unit_to_mm(prm['Y']) if 'Y' in prm else None
            feed = self._unit_to_mm(prm['F']) if 'F' in prm else self.m.feed
            tx = self.m.xpos + x if (x is not None and not self.m.absolute) else x
            ty = self.m.ypos + y if (y is not None and not self.m.absolute) else y
            if tx is None: tx=self.m.xpos
            if ty is None: ty=self.m.ypos
            logging.debug(f"[DEBUG] Linear move: tx={tx}, ty={ty}, feed={feed}, rapid={gcode==0}")
            self.drv.move_abs(tx,ty,feed=feed,rapid=(gcode==0))
            self.m.xpos,self.m.ypos=tx,ty
        elif gcode in (2,3):
            cw = (gcode==2)
            x = self._unit_to_mm(prm['X']) if 'X' in prm else self.m.xpos
            y = self._unit_to_mm(prm['Y']) if 'Y' in prm else self.m.ypos
            i = self._unit_to_mm(prm.get('I',0.0))
            j = self._unit_to_mm(prm.get('J',0.0))
            feed = self._unit_to_mm(prm['F']) if 'F' in prm else self.m.feed
            ex = self.m.xpos + x if (not self.m.absolute) else x
            ey = self.m.ypos + y if (not self.m.absolute) else y
            cx = self.m.xpos + i
            cy = self.m.ypos + j
            start = math.atan2(self.m.ypos-cy, self.m.xpos-cx)
            end   = math.atan2(ey-cy, ex-cx)
            d = end - start
            if cw:
                if d>=0: d-=2*math.pi
            else:
                if d<=0: d+=2*math.pi
            R = math.hypot(self.m.xpos-cx, self.m.ypos-cy)
            e = 0.02
            max_d = 2*math.acos(max(0.0, 1 - e/max(R,1e-9)))
            steps = max(12, int(math.ceil(abs(d)/max(1e-3,max_d))))
            logging.debug(f"[DEBUG] Arc move: ex={ex}, ey={ey}, cx={cx}, cy={cy}, R={R}, steps={steps}")
            for k in range(1, steps+1):
                th = start + d*(k/steps)
                px,py = cx + R*math.cos(th), cy + R*math.sin(th)
                logging.debug(f"[DEBUG] Arc step: px={px}, py={py}, feed={feed}")
                self.drv.move_abs(px,py,feed=feed,rapid=False)
            self.m.xpos,self.m.ypos=ex,ey

    @staticmethod
    def _strip_comment(s):
        """
        Gコード行からコメント部分（()や;以降）を除去
        s: Gコード文字列
        return: コメント除去済み文字列
        """
        s = re.sub(r'\(.*?\)', '', s)
        return s.split(';',1)[0]

# ========= ドライバ =========
class SimDriver:
    def __init__(self):
        """
        シミュレーション用ドライバ。座標履歴（tracks）を記録し、matplotlibで可視化可能。
        """
        self.tracks=[]  # 移動履歴（(x0,y0,x1,y1,rapid,feed)）
        self._cx=0.0    # 現在のX座標
        self._cy=0.0    # 現在のY座標

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
        self._cx=self._cy=0.0

    def move_abs(self,x=None,y=None,feed=None,rapid=False):
        """
        指定座標へ移動（履歴に追加）
        x, y: 移動先座標（Noneなら現状維持）
        feed: 送り速度（未使用）
        rapid: 早送り（Trueなら点線表示）
        """
        nx=self._cx if x is None else float(x)
        ny=self._cy if y is None else float(y)
        logging.debug(f"[DEBUG] SimDriver.move_abs: from=({self._cx},{self._cy}) to=({nx},{ny}), rapid={rapid}, feed={feed}")
        self.tracks.append((self._cx,self._cy,nx,ny,rapid,feed))
        self._cx,self._cy=nx,ny

    def animate_tracks(self, animate=False, fps=2048, title="XY Simulation"):
        """
        移動履歴（tracks）をmatplotlibで可視化
        animate: Trueならアニメーション表示、Falseなら軌跡のみ
        fps: アニメーションのフレームレート
        title: グラフタイトル
        """
        import matplotlib.pyplot as plt
        import matplotlib.animation as animation
        if not self.tracks: print("No tracks"); return
        xs=[p for s in self.tracks for p in (s[0],s[2])]
        ys=[p for s in self.tracks for p in (s[1],s[3])]
        xmin,xmax=min(xs),max(xs); ymin,ymax=min(ys),max(ys)
        pad=0.05*max(xmax-xmin or 1, ymax-ymin or 1)
        fig,ax=plt.subplots(); ax.set_aspect('equal')
        ax.set_xlim(xmin-pad,xmax+pad); ax.set_ylim(ymin-pad,ymax+pad)
        ax.set_xlabel("X [mm]"); ax.set_ylabel("Y [mm]"); ax.set_title(title)
        ax.grid(True, linestyle="--", alpha=0.3); ax.axhline(0,color="0.6"); ax.axvline(0,color="0.6")
        if not animate:
            for (x0,y0,x1,y1,rapid,_) in self.tracks:
                ax.plot([x0,x1],[y0,y1], ':' if rapid else '-', linewidth=1.2 if rapid else 2.0)
            plt.show(); return
        lines=[]; 
        for _ in self.tracks: ln,=ax.plot([],[],'-',lw=2.0); lines.append(ln)
        steps=[max(2,5+int(math.hypot(s[2]-s[0],s[3]-s[1])*2)) for s in self.tracks]
        def data_gen():
            for i,(x0,y0,x1,y1,rapid,_) in enumerate(self.tracks):
                n=steps[i]
                for k in range(1,n+1):
                    t=k/n; yield i,[x0,x0+(x1-x0)*t],[y0,y0+(y1-y0)*t]
        def init():
            for ln in lines: ln.set_data([],[]); return lines
        def update(fr):
            i,xs,ys=fr
            for j in range(i):
                x0,y0,x1,y1,rapid,_=self.tracks[j]
                lines[j].set_data([x0,x1],[y0,y1]); lines[j].set_linestyle(':' if rapid else '-')
            rapid=self.tracks[i][4]; lines[i].set_data(xs,ys); lines[i].set_linestyle(':' if rapid else '-')
            return lines
        anim = animation.FuncAnimation(fig, update, frames=data_gen(), init_func=init,
                                      blit=False, interval=1000/fps, repeat=False, cache_frame_data=False)
        plt.show()

class ChuoDriver:
    def __init__(self, port:str, baud:int=9600, timeout:float=1.0, mm_to_device=None):
        """
        実機（中央精機XYステージ）用ドライバ。シリアル通信で座標指示。
        port: シリアルポート名
        baud: ボーレート
        timeout: タイムアウト秒
        mm_to_device: mm→デバイス座標変換関数
        """
        import serial
        self.ser = serial.Serial(port, baudrate=baud, timeout=timeout)
        time.sleep(0.2)
        self.mm_to_dev = (lambda v: v) if mm_to_device is None else mm_to_device

    def close(self):
        """
        シリアルポートをクローズ
        """
        try: self.ser.close()
        except: pass

    def _write_line(self, s:str):
        """
        コマンド文字列をデバイスへ送信
        s: 送信文字列
        """
        self.ser.write((s+"\r").encode("ascii"))

    def _wait(self):
        """
        通信待ち（短時間スリープ）
        """
        time.sleep(0.01)

    def set_units_mm(self):
        """
        単位をmmに設定（デバイス側で必要なら拡張）
        """
        pass

    def set_units_inch(self):
        """
        単位をinchに設定（デバイス側で必要なら拡張）
        """
        pass

    def home(self):
        """
        原点復帰（デバイス側で必要なら拡張）
        """
        self._wait()

    def move_abs(self,x=None,y=None,feed=None,rapid=False):
        """
        指定座標へ移動コマンド送信
        x, y: 移動先座標（mm単位）
        feed: 送り速度（mm/min）
        rapid: 早送り（Trueならrapid_speed, Falseならcut_speed）
        """
        logging.debug(f"[DEBUG] ChuoDriver.move_abs: x={x}, y={y}, feed={feed}, rapid={rapid}")
        # 速度切り替え
        speed = None
        if rapid:
            speed = getattr(self, "rapid_speed", None)
        else:
            speed = getattr(self, "cut_speed", None)
        # feed優先
        if feed is not None:
            speed = feed
        # コマンド生成
        X=None if x is None else self.mm_to_dev(x)
        Y=None if y is None else self.mm_to_dev(y)
        parts=[]
        if X is not None: parts.append(f"X{int(round(X))}")
        if Y is not None: parts.append(f"Y{int(round(Y))}")
        if speed is not None: parts.append(f"F{int(round(speed))}")
        if parts: self._write_line(" ".join(parts)); self._wait()
    def set_speed_params(self, rapid_speed=None, cut_speed=None):
        """
        早送り・描画時の速度を設定
        rapid_speed: 早送り速度（mm/min）
        cut_speed: 描画速度（mm/min）
        """
        if rapid_speed is not None:
            self.rapid_speed = rapid_speed
        if cut_speed is not None:
            self.cut_speed = cut_speed

# ========= パターン =========
def grid_circles(g, origin, area, cell, circle_d, feed, cw=False, dwell_ms=0, snake=True):
    ox,oy = origin; W,H = area; r = circle_d/2.0
    g.exec("G21 G90"); g.exec(f"F{feed}")
    nx,ny = int(W//cell), int(H//cell)
    base_cx, base_cy = ox+cell/2.0, oy+cell/2.0
    for j in range(ny):
        cols = range(nx) if (not snake or j%2==0) else range(nx-1,-1,-1)
        for i in cols:
            cx = base_cx + i*cell; cy = base_cy + j*cell
            logging.debug(f"[DEBUG] grid_circles: center=({cx:.3f},{cy:.3f})")
            g.exec(f"G0 X{cx:.3f} Y{cy:.3f}")
            g.exec(f"G1 X{(cx+r):.3f} Y{cy:.3f}")
            if cw: g.exec(f"G2 X{(cx+r):.3f} Y{cy:.3f} I{-r:.3f} J0")
            else:  g.exec(f"G3 X{(cx+r):.3f} Y{cy:.3f} I{-r:.3f} J0")
            if dwell_ms>0: time.sleep(dwell_ms/1000.0)

# ---- NEW: SVG → moves ----
def svg_to_moves(g, file_path, origin=(0.0,0.0), px_to_mm=0.264583, chord_mm=0.5,
                 feed=1200.0, y_flip=False, svg_height_mm=None, sort_paths=False):
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
            xs=[]; ys=[]
            for seg in p:
                for t in (0.0, 0.5, 1.0):
                    z = seg.point(t)
                    xs.append(z.real); ys.append(z.imag)
            return (min(xs), min(ys))
        paths = sorted(paths, key=path_key)

    g.exec("G21 G90"); g.exec(f"F{feed}")
    ox, oy = origin

    for path in paths:
        # 各セグメントを chord_mm でサンプリング
        pts = []
        for seg in path:
            seg_len_px = max(1e-9, seg.length(error=1e-5))
            seg_len_mm = seg_len_px * px_to_mm
            steps = max(1, int(math.ceil(seg_len_mm / max(1e-6, chord_mm))))
            for k in range(0, steps+1):
                t = k/steps
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
        for (x,y) in pts[1:]:
            g.exec(f"G1 X{float(x):.3f} Y{float(y):.3f}")

PATTERNS = {
    "grid_circles": grid_circles,
    "svg": svg_to_moves,  # NEW
}

# ========= 対話選択 =========
def select_svg_file():
    """GUIでSVGファイルを選択"""
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        # 隠しウィンドウを作成
        root = tk.Tk()
        root.withdraw()
        
        # ファイルダイアログを表示
        file_path = filedialog.askopenfilename(
            title="SVGファイルを選択してください",
            filetypes=[("SVG files", "*.svg"), ("All files", "*.*")],
            initialdir="."
        )
        
        root.destroy()
        return file_path
    except ImportError:
        print("tkinterが利用できません。ファイルパスを直接入力してください。")
        return input("SVGファイルのパスを入力: ").strip()

def select_config_interactive():
    import glob
    # カレントディレクトリとexamples/ディレクトリのyamlファイルを取得
    yaml_files = [f for f in glob.glob("*.yaml") if f.endswith(".yaml")]
    examples_yaml = [f for f in glob.glob("examples/*.yaml") if f.endswith(".yaml")]
    all_yaml = yaml_files + examples_yaml
    all_yaml.sort()
    if not all_yaml:
        print("YAML設定ファイルが見つかりません。")
        sys.exit(1)
    print("設定ファイルを選択してください:")
    for idx, fname in enumerate(all_yaml, 1):
        print(f"  {idx}: {fname}")
    while True:
        sel = input("番号を入力してください: ").strip()
        if sel.isdigit() and 1 <= int(sel) <= len(all_yaml):
            print(f": {all_yaml[int(sel)-1]}")
            return all_yaml[int(sel)-1]
        print("正しい番号を入力してください。")

# ========= メイン =========
def main():
    # --- コマンドライン引数の解析 ---
    ap = argparse.ArgumentParser(description="Config-driven XY runner (grid/svg)")
    ap.add_argument("--config", help="YAML config path")
    ap.add_argument("--driver", choices=["sim","chuo"])
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--no-animate", action="store_true")
    ap.add_argument("--debug", action="store_true", help="[DEBUG]出力を有効化")
    args = ap.parse_args()

    # --- ログレベル設定 ---
    import logging
    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')
    else:
        logging.basicConfig(level=logging.WARNING, format='%(asctime)s [%(levelname)s] %(message)s')

    # --- 設定ファイル選択・読み込み ---
    config_path = args.config
    if not config_path:
        # config未指定時はusage例を表示し、対話選択
        print("\n[Usage :]")
        print("  python xy_runner.py --config <設定ファイル.yaml>")
        print("  python xy_runner.py --config examples/[SIM]sample_SVG.yaml")
        print("  python xy_runner.py --driver sim --show")
        print("  python xy_runner.py --help")
        print("")
    config_path = select_config_interactive()

    # --- YAML設定ファイルのロード ---
    cfg = yaml.safe_load(open(config_path, "r", encoding="utf-8"))

    # --- ドライバ初期化（sim:シミュレーション, chuo:実機） ---
    driver_name = args.driver or cfg.get("driver","sim")
    mm_per_pulse = cfg.get("mm_per_pulse")
    if driver_name=="sim":
        drv = SimDriver()
    else:
        port = cfg.get("port"); baud = int(cfg.get("baud",9600))
        if not port: raise SystemExit("driver=chuo には port が必要")
        mm_to_dev = (lambda mm: mm/(mm_per_pulse)) if (mm_per_pulse and mm_per_pulse>0) else (lambda mm:mm)
        drv = ChuoDriver(port=port, baud=baud, mm_to_device=mm_to_dev)

    # --- GCodeラッパ初期化 ---
    g = GCodeWrapper(drv)

    # --- デフォルト設定（単位・座標モード・送り速度） ---
    d = cfg.get("defaults", {})
    if d.get("unit","mm")=="mm": g.exec("G21")
    else: g.exec("G20")
    if d.get("mode","absolute")=="absolute": g.exec("G90")
    else: g.exec("G91")
    if "feed" in d: g.exec(f"F{float(d['feed'])}")

    # --- ジョブ（jobs）実行 ---
    for job in cfg.get("jobs", []):
        typ = job["type"]
        if typ not in PATTERNS: raise SystemExit(f"unknown pattern: {typ}")
        if typ=="grid_circles":
            # グリッド円パターンの描画
            PATTERNS[typ](
                g,
                origin=job.get("origin",[0,0]),
                area=job.get("area",[100,100]),
                cell=float(job.get("cell",20)),
                circle_d=float(job.get("circle_d",20)),
                feed=float(job.get("feed", d.get("feed",1200))),
                cw=bool(job.get("cw", False)),
                dwell_ms=int(job.get("dwell_ms",0)),
                snake=bool(job.get("snake", True)),
            )
        elif typ=="svg":
            # SVGパスの描画
            file_path = job.get("file")
            # fileが未指定・空文字列・Noneなら必ず対話選択
            if not file_path or str(file_path).strip() == "":
                print("SVGファイルが指定されていません。ファイルを選択してください...")
                file_path = select_svg_file()
                if not file_path:
                    print("SVGファイルが選択されませんでした。スキップします。")
                    continue
                print(f"選択されたSVGファイル: {file_path}")
            px_to_mm = float(job.get("px_to_mm", 0.264583))  # 96dpi基準
            chord_mm = float(job.get("chord_mm", 0.5))
            origin = job.get("origin", [0,0])
            feed = float(job.get("feed", d.get("feed",1200)))
            y_flip = bool(job.get("y_flip", False))
            svg_height_mm = job.get("svg_height_mm", None)
            if svg_height_mm is not None:
                svg_height_mm = float(svg_height_mm)
            sort_paths = bool(job.get("sort_paths", False))
            PATTERNS[typ](
                g,
                file_path=file_path,
                origin=origin,
                px_to_mm=px_to_mm,
                chord_mm=chord_mm,
                feed=feed,
                y_flip=y_flip,
                svg_height_mm=svg_height_mm,
                sort_paths=sort_paths,
            )

    # --- シミュレーション表示 or 実機クローズ ---
    vis = cfg.get("visual", {})
    show_flag = args.show or bool(vis.get("show", False))
    if driver_name=="sim" and show_flag:
        # シミュレーション軌跡表示
        title = vis.get("title","XY Simulation")
        animate = not args.no_animate and bool(vis.get("animate", True))
        drv.animate_tracks(animate=animate, title=title)
    else:
        # 実機ドライバのクローズ処理
        if hasattr(drv,"close"): drv.close()

if __name__ == "__main__":
    main()
