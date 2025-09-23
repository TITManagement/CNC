#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modified xy_runner.py with debug output
"""
import math, re, time, argparse, yaml, os
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
        self.debug = True  # デバッグ有効

    def exec(self, line: str):
        if self.debug:
            print(f"DEBUG: Executing: {line}")
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
        if any(w.upper().startswith(t) for t in ('G0','G1','G2','G3')):
            if self.debug:
                print(f"DEBUG: Motion detected in: {words}")
            self._motion(words)

    def _unit_to_mm(self, v): return v if self.m.units_mm else v*25.4

    def _motion(self, words):
        if self.debug:
            print(f"DEBUG: _motion called with: {words}")
        gcode, prm = None, {}
        for w in words:
            c,v=w[0].upper(),w[1:]
            if c=='G': gcode=int(float(v))
            elif c in ('X','Y','I','J','F'): prm[c]=float(v)
        if self.debug:
            print(f"DEBUG: gcode={gcode}, prm={prm}")
        if gcode in (0,1):
            x = self._unit_to_mm(prm['X']) if 'X' in prm else None
            y = self._unit_to_mm(prm['Y']) if 'Y' in prm else None
            feed = self._unit_to_mm(prm['F']) if 'F' in prm else self.m.feed
            tx = self.m.xpos + x if (x is not None and not self.m.absolute) else x
            ty = self.m.ypos + y if (y is not None and not self.m.absolute) else y
            if tx is None: tx=self.m.xpos
            if ty is None: ty=self.m.ypos
            if self.debug:
                print(f"DEBUG: Moving from ({self.m.xpos}, {self.m.ypos}) to ({tx}, {ty})")
            self.drv.move_abs(tx,ty,feed=feed,rapid=(gcode==0))
            self.m.xpos,self.m.ypos=tx,ty
        elif gcode in (2,3):
            if self.debug:
                print(f"DEBUG: Arc motion G{gcode}")
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
            if self.debug:
                print(f"DEBUG: Arc steps={steps}, R={R}")
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
    def __init__(self): 
        self.tracks=[]
        self._cx=0.0
        self._cy=0.0
        self.debug = True
    def set_units_mm(self): pass
    def set_units_inch(self): pass
    def home(self): self._cx=self._cy=0.0
    def move_abs(self,x=None,y=None,feed=None,rapid=False):
        nx=self._cx if x is None else float(x)
        ny=self._cy if y is None else float(y)
        if self.debug:
            print(f"DEBUG: SimDriver.move_abs: ({self._cx}, {self._cy}) -> ({nx}, {ny})")
        self.tracks.append((self._cx,self._cy,nx,ny,rapid,feed))
        self._cx,self._cy=nx,ny
    def show(self,animate=False,fps=60,title="XY Simulation"):
        import matplotlib.pyplot as plt
        import matplotlib.animation as animation
        print(f"DEBUG: SimDriver.show called, tracks count: {len(self.tracks)}")
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
        animation.FuncAnimation(fig, update, frames=data_gen(), init_func=init,
                                blit=False, interval=1000/fps, repeat=False)
        plt.show()

# ========= パターン =========
def grid_circles(g, origin, area, cell, circle_d, feed, cw=False, dwell_ms=0, snake=True):
    print(f"DEBUG: grid_circles called")
    ox,oy = origin; W,H = area; r = circle_d/2.0
    g.exec("G21 G90"); g.exec(f"F{feed}")
    nx,ny = int(W//cell), int(H//cell)
    base_cx, base_cy = ox+cell/2.0, oy+cell/2.0
    print(f"DEBUG: Grid {nx}x{ny}, base_center=({base_cx}, {base_cy})")
    for j in range(ny):
        cols = range(nx) if (not snake or j%2==0) else range(nx-1,-1,-1)
        for i in cols:
            cx = base_cx + i*cell; cy = base_cy + j*cell
            print(f"DEBUG: Circle at ({cx}, {cy}), r={r}")
            g.exec(f"G0 X{cx:.3f} Y{cy:.3f}")
            g.exec(f"G1 X{(cx+r):.3f} Y{cy:.3f}")
            if cw: g.exec(f"G2 X{(cx+r):.3f} Y{cy:.3f} I{-r:.3f} J0")
            else:  g.exec(f"G3 X{(cx+r):.3f} Y{cy:.3f} I{-r:.3f} J0")
            if dwell_ms>0: time.sleep(dwell_ms/1000.0)

PATTERNS = {
    "grid_circles": grid_circles,
}

# ========= メイン =========
def main():
    print("DEBUG: Starting main()")
    ap = argparse.ArgumentParser(description="Debug version")
    ap.add_argument("--config", required=True, help="YAML config path")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config, "r", encoding="utf-8"))
    driver_name = "sim"  # Force sim for debug

    drv = SimDriver()
    g = GCodeWrapper(drv)

    # defaults
    d = cfg.get("defaults", {})
    if d.get("unit","mm")=="mm": g.exec("G21")
    else: g.exec("G20")
    if d.get("mode","absolute")=="absolute": g.exec("G90")
    else: g.exec("G91")
    if "feed" in d: g.exec(f"F{float(d['feed'])}")

    # jobs
    print(f"DEBUG: Processing {len(cfg.get('jobs', []))} jobs")
    for job in cfg.get("jobs", []):
        typ = job["type"]
        print(f"DEBUG: Job type: {typ}")
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

    # show
    print(f"DEBUG: Final track count: {len(drv.tracks)}")
    if drv.tracks:
        print("First few tracks:")
        for i, track in enumerate(drv.tracks[:3]):
            print(f"  {i}: {track}")
    drv.show(animate=False, title="Debug View")

if __name__ == "__main__":
    main()