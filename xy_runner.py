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
        self.drv = driver
        self.m = ModalState()

    def exec(self, line: str):
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

    def _unit_to_mm(self, v): return v if self.m.units_mm else v*25.4

    def _motion(self, words):
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
            for k in range(1, steps+1):
                th = start + d*(k/steps)
                px,py = cx + R*math.cos(th), cy + R*math.sin(th)
                self.drv.move_abs(px,py,feed=feed,rapid=False)
            self.m.xpos,self.m.ypos=ex,ey

    @staticmethod
    def _strip_comment(s):
        s = re.sub(r'\(.*?\)', '', s)
        return s.split(';',1)[0]

# ========= ドライバ =========
class SimDriver:
    def __init__(self): self.tracks=[]; self._cx=0.0; self._cy=0.0
    def set_units_mm(self): pass
    def set_units_inch(self): pass
    def home(self): self._cx=self._cy=0.0
    def move_abs(self,x=None,y=None,feed=None,rapid=False):
        nx=self._cx if x is None else float(x)
        ny=self._cy if y is None else float(y)
        self.tracks.append((self._cx,self._cy,nx,ny,rapid,feed))
        self._cx,self._cy=nx,ny
    def show(self,animate=False,fps=75,title="XY Simulation"):
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
        import serial
        self.ser = serial.Serial(port, baudrate=baud, timeout=timeout)
        time.sleep(0.2)
        self.mm_to_dev = (lambda v: v) if mm_to_device is None else mm_to_device
    def close(self):
        try: self.ser.close()
        except: pass
    def _write_line(self, s:str): self.ser.write((s+"\r").encode("ascii"))
    def _wait(self): time.sleep(0.01)
    def set_units_mm(self): pass
    def set_units_inch(self): pass
    def home(self): self._wait()
    def move_abs(self,x=None,y=None,feed=None,rapid=False):
        X=None if x is None else self.mm_to_dev(x)
        Y=None if y is None else self.mm_to_dev(y)
        parts=[]; 
        if X is not None: parts.append(f"X{int(round(X))}")
        if Y is not None: parts.append(f"Y{int(round(Y))}")
        if parts: self._write_line(" ".join(parts)); self._wait()

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
    yaml_files = [f for f in glob.glob("*.yaml") if f.endswith(".yaml")]
    if not yaml_files:
        print("YAML設定ファイルが見つかりません。")
        sys.exit(1)
    print("設定ファイルを選択してください:")
    for idx, fname in enumerate(yaml_files, 1):
        print(f"  {idx}: {fname}")
    while True:
        sel = input("番号を入力してください: ").strip()
        if sel.isdigit() and 1 <= int(sel) <= len(yaml_files):
            return yaml_files[int(sel)-1]
        print("正しい番号を入力してください。")

# ========= メイン =========
def main():
    ap = argparse.ArgumentParser(description="Config-driven XY runner (grid/svg)")
    ap.add_argument("--config", help="YAML config path")
    ap.add_argument("--driver", choices=["sim","chuo"])
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--no-animate", action="store_true")
    args = ap.parse_args()

    # config未指定時は対話選択
    config_path = args.config
    if not config_path:
        config_path = select_config_interactive()
        print(f"選択された設定: {config_path}")

    cfg = yaml.safe_load(open(config_path, "r", encoding="utf-8"))
    driver_name = args.driver or cfg.get("driver","sim")
    mm_per_pulse = cfg.get("mm_per_pulse")

    if driver_name=="sim":
        drv = SimDriver()
    else:
        port = cfg.get("port"); baud = int(cfg.get("baud",9600))
        if not port: raise SystemExit("driver=chuo には port が必要")
        mm_to_dev = (lambda mm: mm/(mm_per_pulse)) if (mm_per_pulse and mm_per_pulse>0) else (lambda mm:mm)
        drv = ChuoDriver(port=port, baud=baud, mm_to_device=mm_to_dev)

    g = GCodeWrapper(drv)

    # defaults
    d = cfg.get("defaults", {})
    if d.get("unit","mm")=="mm": g.exec("G21")
    else: g.exec("G20")
    if d.get("mode","absolute")=="absolute": g.exec("G90")
    else: g.exec("G91")
    if "feed" in d: g.exec(f"F{float(d['feed'])}")

    # jobs
    for job in cfg.get("jobs", []):
        typ = job["type"]
        if typ not in PATTERNS: raise SystemExit(f"unknown pattern: {typ}")
        if typ=="grid_circles":
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
            # SVG job params
            file_path = job.get("file")
            if not file_path:
                # ファイルパスが指定されていない場合、GUIで選択
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

    # show/close
    vis = cfg.get("visual", {})
    show_flag = args.show or bool(vis.get("show", False))
    if driver_name=="sim" and show_flag:
        title = vis.get("title","XY Simulation")
        animate = not args.no_animate and bool(vis.get("animate", True))
        drv.show(animate=animate, title=title)
    else:
        if hasattr(drv,"close"): drv.close()

if __name__ == "__main__":
    main()
