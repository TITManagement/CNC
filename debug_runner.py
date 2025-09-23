#!/usr/bin/env python3
import yaml
import math
import re

# 簡単なデバッグ版
class DebugDriver:
    def __init__(self):
        self.tracks = []
        self._cx = 0.0
        self._cy = 0.0
        self.commands = []

    def set_units_mm(self):
        self.commands.append("SET_UNITS_MM")

    def set_units_inch(self):
        self.commands.append("SET_UNITS_INCH")

    def home(self):
        self._cx = self._cy = 0.0
        self.commands.append("HOME")

    def move_abs(self, x=None, y=None, feed=None, rapid=False):
        nx = self._cx if x is None else float(x)
        ny = self._cy if y is None else float(y)
        self.tracks.append((self._cx, self._cy, nx, ny, rapid, feed))
        self._cx, self._cy = nx, ny
        self.commands.append(f"MOVE_ABS x={nx:.3f} y={ny:.3f} feed={feed} rapid={rapid}")
        print(f"Track added: ({self._cx:.3f}, {self._cy:.3f}) -> ({nx:.3f}, {ny:.3f})")

class DebugModalState:
    def __init__(self):
        self.units_mm = True
        self.absolute = True
        self.feed = 1200.0
        self.xpos = 0.0
        self.ypos = 0.0

class DebugGCodeWrapper:
    def __init__(self, driver):
        self.drv = driver
        self.m = DebugModalState()
        self.command_count = 0

    def exec(self, line: str):
        self.command_count += 1
        print(f"Command {self.command_count}: {line}")
        
        line = self._strip_comment(line).strip()
        if not line:
            print("  -> Empty command")
            return
            
        if line.startswith("$H"):
            print("  -> HOME")
            self.drv.home()
            return
            
        words = re.findall(r'[A-Za-z][+\-0-9\.]*', line)
        print(f"  -> Words: {words}")
        
        # モーダル処理
        for w in words:
            c, v = w[0].upper(), w[1:]
            if c == 'G':
                g = float(v)
                if g == 20:
                    self.m.units_mm = False
                    self.drv.set_units_inch()
                    print(f"  -> Set units: INCH")
                if g == 21:
                    self.m.units_mm = True
                    self.drv.set_units_mm()
                    print(f"  -> Set units: MM")
                if g == 90:
                    self.m.absolute = True
                    print(f"  -> Set mode: ABSOLUTE")
                if g == 91:
                    self.m.absolute = False
                    print(f"  -> Set mode: RELATIVE")
                    
        for w in words:
            if w[0].upper() == 'F':
                self.m.feed = float(w[1:])
                print(f"  -> Set feed: {self.m.feed}")
                
        # 動作処理
        if any(w.upper().startswith(t) for t in ('G0', 'G1', 'G2', 'G3')):
            print("  -> Motion command detected")
            self._motion(words)

    def _unit_to_mm(self, v):
        return v if self.m.units_mm else v * 25.4

    def _motion(self, words):
        gcode, prm = None, {}
        for w in words:
            c, v = w[0].upper(), w[1:]
            if c == 'G':
                gcode = int(float(v))
            elif c in ('X', 'Y', 'I', 'J', 'F'):
                prm[c] = float(v)
                
        print(f"    Motion: G{gcode}, params: {prm}")
        
        if gcode in (0, 1):
            x = self._unit_to_mm(prm['X']) if 'X' in prm else None
            y = self._unit_to_mm(prm['Y']) if 'Y' in prm else None
            feed = self._unit_to_mm(prm['F']) if 'F' in prm else self.m.feed
            
            tx = self.m.xpos + x if (x is not None and not self.m.absolute) else x
            ty = self.m.ypos + y if (y is not None and not self.m.absolute) else y
            
            if tx is None:
                tx = self.m.xpos
            if ty is None:
                ty = self.m.ypos
                
            print(f"    -> Moving from ({self.m.xpos:.3f}, {self.m.ypos:.3f}) to ({tx:.3f}, {ty:.3f})")
            
            self.drv.move_abs(tx, ty, feed=feed, rapid=(gcode == 0))
            self.m.xpos, self.m.ypos = tx, ty

    @staticmethod
    def _strip_comment(s):
        s = re.sub(r'\(.*?\)', '', s)
        return s.split(';', 1)[0]

def debug_grid_circles(g, origin, area, cell, circle_d, feed, cw=False, dwell_ms=0, snake=True):
    print(f"Starting grid_circles: origin={origin}, area={area}, cell={cell}, circle_d={circle_d}")
    print(f"  feed={feed}, cw={cw}, dwell_ms={dwell_ms}, snake={snake}")
    
    ox, oy = origin
    W, H = area
    r = circle_d / 2.0
    
    print(f"  Calculated: ox={ox}, oy={oy}, W={W}, H={H}, r={r}")
    
    g.exec("G21 G90")
    g.exec(f"F{feed}")
    
    nx, ny = int(W // cell), int(H // cell)
    print(f"  Grid size: nx={nx}, ny={ny}")
    
    base_cx, base_cy = ox + cell / 2.0, oy + cell / 2.0
    print(f"  Base center: ({base_cx}, {base_cy})")
    
    for j in range(ny):
        cols = range(nx) if (not snake or j % 2 == 0) else range(nx - 1, -1, -1)
        print(f"  Row {j}: columns = {list(cols)}")
        
        for i in cols:
            cx = base_cx + i * cell
            cy = base_cy + j * cell
            print(f"    Cell ({i}, {j}): center = ({cx:.3f}, {cy:.3f})")
            
            g.exec(f"G0 X{cx:.3f} Y{cy:.3f}")
            g.exec(f"G1 X{(cx + r):.3f} Y{cy:.3f}")
            
            if cw:
                g.exec(f"G2 X{(cx + r):.3f} Y{cy:.3f} I{-r:.3f} J0")
            else:
                g.exec(f"G3 X{(cx + r):.3f} Y{cy:.3f} I{-r:.3f} J0")

# メイン実行
cfg = yaml.safe_load(open('job.yaml', 'r', encoding='utf-8'))
print("=== Configuration ===")
print(yaml.dump(cfg, default_flow_style=False))

drv = DebugDriver()
g = DebugGCodeWrapper(drv)

print("\n=== Executing jobs ===")
for i, job in enumerate(cfg.get("jobs", [])):
    print(f"\nJob {i}: {job}")
    
    if job["type"] == "grid_circles":
        debug_grid_circles(
            g,
            origin=job.get("origin", [0, 0]),
            area=job.get("area", [100, 100]),
            cell=float(job.get("cell", 20)),
            circle_d=float(job.get("circle_d", 20)),
            feed=float(job.get("feed", cfg.get("defaults", {}).get("feed", 1200))),
            cw=bool(job.get("cw", False)),
            dwell_ms=int(job.get("dwell_ms", 0)),
            snake=bool(job.get("snake", True)),
        )

print(f"\n=== Results ===")
print(f"Total tracks generated: {len(drv.tracks)}")
print(f"Total commands executed: {g.command_count}")
print(f"Driver commands: {len(drv.commands)}")

if drv.tracks:
    print("\nFirst few tracks:")
    for i, track in enumerate(drv.tracks[:5]):
        print(f"  {i}: {track}")
else:
    print("No tracks generated!")