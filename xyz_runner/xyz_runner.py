#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Config-driven XYZ runner (3D) - Cross-platform support
- Platforms: Windows, macOS, Linux (Ubuntu 24.04)
- Drivers: sim / chuo (XYZ)
- Jobs: grid_spheres, gcode, stp
Dependencies:
  pip install pyyaml matplotlib pyserial numpy svgpathtools pythonocc-core
"""
import math, re, time, argparse, yaml, os, sys, platform
from dataclasses import dataclass
import threading
import queue
import matplotlib.pyplot as plt
import numpy as np
import time
import logging
from pathlib import Path

# ========= プラットフォーム対応ユーティリティ =========
class PlatformUtils:
    """クロスプラットフォーム対応のユーティリティクラス"""
    
    @staticmethod
    def get_platform_info():
        """プラットフォーム情報を取得"""
        system = platform.system().lower()
        return {
            'system': system,
            'is_windows': system == 'windows',
            'is_macos': system == 'darwin',
            'is_linux': system == 'linux',
            'version': platform.version(),
            'machine': platform.machine()
        }
    
    @staticmethod
    def get_default_serial_ports():
        """プラットフォーム別のデフォルトシリアルポート候補を返す"""
        pinfo = PlatformUtils.get_platform_info()
        if pinfo['is_windows']:
            return ['COM1', 'COM2', 'COM3', 'COM4', 'COM5']
        elif pinfo['is_macos']:
            return ['/dev/tty.usbserial-*', '/dev/tty.usbmodem*', '/dev/cu.usbserial-*']
        else:  # Linux
            return ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/ttyACM1']
    
    @staticmethod
    def normalize_path(path_str):
        """パスを正規化（プラットフォーム依存の区切り文字を統一）"""
        return str(Path(path_str).resolve())
    
    @staticmethod
    def get_venv_activate_command():
        """仮想環境の活性化コマンドを取得"""
        pinfo = PlatformUtils.get_platform_info()
        if pinfo['is_windows']:
            return '.venv\\Scripts\\activate.bat'
        else:
            return 'source .venv/bin/activate'
    
    @staticmethod
    def get_python_executable():
        """Pythonの実行可能ファイル名を取得"""
        pinfo = PlatformUtils.get_platform_info()
        if pinfo['is_windows']:
            return 'python.exe'
        else:
            return 'python3'

# ========= 共通（簡易Gコードラッパ：直線/円弧/3D） =========
@dataclass
class ModalState3D:
    units_mm: bool = True
    absolute: bool = True
    feed: float = 1200.0
    xpos: float = 0.0
    ypos: float = 0.0
    zpos: float = 0.0

class GCodeWrapper3D:
    def __init__(self, driver):
        self.drv = driver
        self.m = ModalState3D()

    def exec(self, line: str):
        logging.debug(f"[DEBUG] GCodeWrapper3D.exec: line='{line}'")
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
        return v if self.m.units_mm else v*25.4

    def _motion(self, words):
        gcode, prm = None, {}
        for w in words:
            c,v=w[0].upper(),w[1:]
            if c=='G': gcode=int(float(v))
            elif c in ('X','Y','Z','I','J','K','F'): prm[c]=float(v)
        if gcode in (0,1):
            x = self._unit_to_mm(prm['X']) if 'X' in prm else None
            y = self._unit_to_mm(prm['Y']) if 'Y' in prm else None
            z = self._unit_to_mm(prm['Z']) if 'Z' in prm else None
            feed = self._unit_to_mm(prm['F']) if 'F' in prm else self.m.feed
            tx = self.m.xpos + x if (x is not None and not self.m.absolute) else x
            ty = self.m.ypos + y if (y is not None and not self.m.absolute) else y
            tz = self.m.zpos + z if (z is not None and not self.m.absolute) else z
            if tx is None: tx=self.m.xpos
            if ty is None: ty=self.m.ypos
            if tz is None: tz=self.m.zpos
            logging.debug(f"[DEBUG] Linear move: tx={tx}, ty={ty}, tz={tz}, feed={feed}, rapid={gcode==0}")
            self.drv.move_abs(tx,ty,tz,feed=feed,rapid=(gcode==0))
            self.m.xpos,self.m.ypos,self.m.zpos=tx,ty,tz
        # 円弧・3Dパスは省略（必要に応じて拡張）

    @staticmethod
    def _strip_comment(s):
        s = re.sub(r'\(.*?\)', '', s)
        return s.split(';',1)[0]

# ========= ドライバ（3Dシミュレーション/実機） =========
class SimDriver3D:
    def __init__(self):
        self.tracks=[]  # 移動履歴（(x0,y0,z0,x1,y1,z1,rapid,feed)）
        self._cx=0.0; self._cy=0.0; self._cz=0.0
    def set_units_mm(self): pass
    def set_units_inch(self): pass
    def home(self): self._cx=self._cy=self._cz=0.0
    def move_abs(self,x=None,y=None,z=None,feed=None,rapid=False):
        nx=self._cx if x is None else float(x)
        ny=self._cy if y is None else float(y)
        nz=self._cz if z is None else float(z)
        logging.debug(f"[DEBUG] SimDriver3D.move_abs: from=({self._cx},{self._cy},{self._cz}) to=({nx},{ny},{nz}), rapid={rapid}, feed={feed}")
        self.tracks.append((self._cx,self._cy,self._cz,nx,ny,nz,rapid,feed))
        self._cx,self._cy,self._cz=nx,ny,nz
    def animate_tracks(self, animate=True, fps=1080, title="XYZ Simulation"):
        """
        移動履歴（tracks）を3Dでmatplotlibで可視化
        animate: Trueならアニメーション表示、Falseなら軌跡のみ
        fps: アニメーションのフレームレート
        title: グラフタイトル
        """
        import matplotlib.pyplot as plt
        import matplotlib.animation as animation
        from mpl_toolkits.mplot3d import Axes3D
        if not self.tracks: print("No tracks"); return
        
        # 座標範囲を計算
        xs=[p for s in self.tracks for p in (s[0],s[3])]
        ys=[p for s in self.tracks for p in (s[1],s[4])]
        zs=[p for s in self.tracks for p in (s[2],s[5])]
        xmin,xmax=min(xs),max(xs); ymin,ymax=min(ys),max(ys); zmin,zmax=min(zs),max(zs)
        pad=0.05*max(xmax-xmin or 1, ymax-ymin or 1, zmax-zmin or 1)
        
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        ax.set_xlim(xmin-pad,xmax+pad); ax.set_ylim(ymin-pad,ymax+pad); ax.set_zlim(zmin-pad,zmax+pad)
        ax.set_xlabel("X [mm]"); ax.set_ylabel("Y [mm]"); ax.set_zlabel("Z [mm]"); ax.set_title(title)
        ax.grid(True, alpha=0.3)
        
        if not animate:
            # 静的表示
            for (x0,y0,z0,x1,y1,z1,rapid,_) in self.tracks:
                ax.plot([x0,x1],[y0,y1],[z0,z1], ':' if rapid else '-', 
                       linewidth=1.2 if rapid else 2.0, alpha=0.8)
            plt.show(); return
        
        # アニメーション表示
        lines=[]; 
        for _ in self.tracks: 
            ln, = ax.plot([],[],[], '-', lw=2.0, alpha=0.8); lines.append(ln)
        
        # 各線分のステップ数を計算
        steps=[]
        for (x0,y0,z0,x1,y1,z1,rapid,_) in self.tracks:
            dist = math.sqrt((x1-x0)**2 + (y1-y0)**2 + (z1-z0)**2)
            step_count = max(3, int(dist * 2) + 5)  # 距離に応じてステップ数調整
            steps.append(step_count)
        
        def data_gen():
            for i,(x0,y0,z0,x1,y1,z1,rapid,_) in enumerate(self.tracks):
                n=steps[i]
                for k in range(1,n+1):
                    t=k/n
                    x = x0+(x1-x0)*t
                    y = y0+(y1-y0)*t  
                    z = z0+(z1-z0)*t
                    yield i,[x0,x],[y0,y],[z0,z],rapid
        
        def init():
            for ln in lines: ln.set_data_3d([],[],[]); 
            return lines
            
        def update(data):
            i,xs,ys,zs,rapid=data
            # 過去の線分を描画（完了済み）
            for j in range(i):
                x0,y0,z0,x1,y1,z1,r,_=self.tracks[j]
                lines[j].set_data_3d([x0,x1],[y0,y1],[z0,z1])
                lines[j].set_linestyle(':' if r else '-')
                lines[j].set_color('gray' if r else 'blue')
            # 現在の線分を描画（進行中）
            if i < len(lines):
                lines[i].set_data_3d(xs,ys,zs)
                lines[i].set_linestyle(':' if rapid else '-')
                lines[i].set_color('red' if rapid else 'green')
            return lines
            
        anim = animation.FuncAnimation(fig, update, frames=data_gen(), init_func=init,
                                      blit=False, interval=1000/fps, repeat=False, 
                                      cache_frame_data=False)
        plt.show()

# ========= 3Dパターン =========
def grid_spheres_3d(g, origin, area, cell, sphere_d, feed, levels=3):
    """
    3Dグリッド球体パターンを生成（Z=0から開始）
    origin: [x, y, z] 原点座標
    area: [w, h, d] XYZ範囲
    cell: セル間隔
    sphere_d: 球体直径
    feed: 送り速度
    levels: Z方向のレベル数
    """
    ox, oy, oz = origin
    W, H, D = area
    r = sphere_d / 2.0
    
    g.exec("G21 G90")  # mm, absolute
    g.exec(f"F{feed}")
    g.exec("G0 Z0")    # Z=0から開始
    
    nx, ny, nz = int(W//cell), int(H//cell), int(D//cell)
    base_cx, base_cy, base_cz = ox + cell/2.0, oy + cell/2.0, oz + cell/2.0
    
    print(f"3Dグリッド: {nx}x{ny}x{nz} = {nx*ny*nz}個の球体 (Z=0から開始)")
    
    total_spheres = 0
    for k in range(nz):  # Z方向
        for j in range(ny):  # Y方向
            for i in range(nx):  # X方向
                cx = base_cx + i * cell
                cy = base_cy + j * cell
                cz = base_cz + k * cell
                
                logging.debug(f"[DEBUG] grid_spheres_3d: center=({cx:.3f},{cy:.3f},{cz:.3f})")
                
                # 球体をZ方向のレベルで分割（Z=0から上方向）
                for level in range(levels):
                    # Z=0から球体上部まで
                    z_offset = (level / levels) * 2 * r - r  # -r から +r
                    z_pos = max(0, cz + z_offset)  # Z=0未満は0にクランプ
                    
                    # 切断面での円の半径（XY平面）
                    if abs(z_offset) <= r:
                        circle_r = math.sqrt(r*r - z_offset*z_offset)
                        if circle_r > 0.5:  # 最小半径
                            steps = max(6, int(circle_r * 4))
                            
                            # 円の開始点へ移動
                            if level == 0:
                                g.exec(f"G0 X{cx + circle_r:.3f} Y{cy:.3f} Z0")  # 最初は必ずZ=0
                            else:
                                g.exec(f"G0 X{cx + circle_r:.3f} Y{cy:.3f} Z{z_pos:.3f}")
                            
                            # XY平面で円を描画
                            for step in range(steps + 1):
                                angle = 2 * math.pi * step / steps
                                x = cx + circle_r * math.cos(angle)
                                y = cy + circle_r * math.sin(angle)
                                
                                if level == 0:
                                    g.exec(f"G1 X{x:.3f} Y{y:.3f} Z0")  # 最初のレベルはZ=0
                                else:
                                    g.exec(f"G1 X{x:.3f} Y{y:.3f} Z{z_pos:.3f}")
                
                total_spheres += 1
    
    print(f"合計 {total_spheres} 個の球体を描画しました")
    return f"3Dグリッド球体パターンを実行しました (cell={cell}mm, sphere_d={sphere_d}mm)"

# ========= G-code/STEPファイル読み込み =========
def load_gcode_or_stp(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext in ['.gcode', '.nc', '.tap']:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        return 'gcode', lines
    elif ext in ['.stp', '.step']:
        try:
            from OCC.Core.STEPControl import STEPControl_Reader
            from OCC.Core.IFSelect import IFSelect_RetDone
            reader = STEPControl_Reader()
            status = reader.ReadFile(file_path)
            if status != IFSelect_RetDone:
                raise Exception("STEPファイルの読み込みに失敗しました")
            reader.TransferRoots()
            shape = reader.Shape()
            return 'stp', shape
        except Exception as e:
            print(f"STEPファイル読み込みエラー: {e}"); return None, None
    else:
        print("未対応ファイル形式: ", ext); return None, None

def process_step_file_simple(g, file_path, origin, resolution):
    """
    STEPファイルの簡易処理（球体形状を近似）
    実際の実装では pythonocc-core を使用
    """
    ox, oy, oz = origin
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # STEPファイルから球体情報を抽出（改良版パーサー）
    spheres = []
    lines = content.split('\n')
    
    # まず球体表面を検出
    sphere_surfaces = {}
    for line in lines:
        if 'SPHERICAL_SURFACE' in line:
            parts = line.split('=')[0].strip('#')
            if parts.isdigit():
                entity_id = int(parts)
                # 半径を抽出
                if ',' in line:
                    try:
                        radius_part = line.split(',')[-1].replace(')', '').replace(';', '').strip()
                        radius = float(radius_part)
                        sphere_surfaces[entity_id] = radius
                    except (ValueError, IndexError):
                        sphere_surfaces[entity_id] = 10.0  # デフォルト半径
    
    # 座標点を検出
    points = {}
    for line in lines:
        if 'CARTESIAN_POINT' in line:
            parts = line.split('=')[0].strip('#')
            if parts.isdigit():
                entity_id = int(parts)
                if '(' in line and ')' in line:
                    coords_str = line[line.find('(')+1:line.rfind(')')]
                    coord_parts = [p.strip() for p in coords_str.split(',')]
                    if len(coord_parts) >= 3:
                        try:
                            # 最後の3つの数値を座標として取得
                            coords = []
                            for part in coord_parts[-3:]:
                                if part.replace('.', '').replace('-', '').isdigit():
                                    coords.append(float(part))
                            if len(coords) == 3:
                                points[entity_id] = coords
                        except ValueError:
                            continue
    
    # デフォルトの球体を追加（パースに失敗した場合）
    if not sphere_surfaces:
        print("STEPファイルの解析に失敗。デフォルト球体を使用")
        spheres = [
            {'center': (0, 0, 0), 'radius': 10.0},
            {'center': (20, 0, 0), 'radius': 7.0},
            {'center': (0, 20, 10), 'radius': 3.0}
        ]
    else:
        # 検出した球体情報を統合
        for surface_id, radius in sphere_surfaces.items():
            # 対応する中心点を検索（近い番号のポイントを使用）
            center = (0, 0, 0)  # デフォルト
            for point_id, coords in points.items():
                if abs(point_id - surface_id) <= 2:  # 近い番号のポイント
                    center = tuple(coords)
                    break
            spheres.append({'center': center, 'radius': radius})
    
    print(f"STEPファイルから {len(spheres)} 個の球体を検出")
    
    # 各球体を近似的に描画
    for i, sphere in enumerate(spheres):
        cx, cy, cz = sphere['center']
        r = sphere['radius']
        cx += ox; cy += oy; cz += oz
        
        print(f"球体 {i+1}: 中心=({cx:.1f},{cy:.1f},{cz:.1f}), 半径={r:.1f}")
        
        # 球体をXY平面（Z軸方向）で複数レベルに分割
        levels = max(3, int(r / resolution))
        
        # Z=0から開始し、球体の下半分から上半分へ
        for level in range(levels + 1):
            # Z座標での水平切断面（Z=0から開始）
            z_offset = (level / levels) * 2 * r - r  # -r から +r
            z_pos = cz + z_offset
            
            # 切断面での円の半径（XY平面）
            if abs(z_offset) <= r:
                circle_r = math.sqrt(r*r - z_offset*z_offset)
                if circle_r > 0.1:  # 最小半径制限
                    # XY平面で円を描画
                    steps = max(8, int(circle_r * 6))
                    
                    # Z=0から開始する場合の特別処理
                    if level == 0:
                        print(f"  Z=0レベルから開始: 半径={circle_r:.2f}mm")
                        g.exec(f"G0 X{cx + circle_r:.3f} Y{cy:.3f} Z0")  # Z=0から開始
                    else:
                        g.exec(f"G0 X{cx + circle_r:.3f} Y{cy:.3f} Z{z_pos:.3f}")
                    
                    for step in range(steps + 1):
                        angle = 2 * math.pi * step / steps
                        x = cx + circle_r * math.cos(angle)
                        y = cy + circle_r * math.sin(angle)
                        
                        # 最初のレベル（Z=0）は常にZ=0で描画
                        if level == 0:
                            g.exec(f"G1 X{x:.3f} Y{y:.3f} Z0")
                        else:
                            g.exec(f"G1 X{x:.3f} Y{y:.3f} Z{z_pos:.3f}")

def select_file_with_dialog(title, filetypes):
    """GUIでファイルを選択（クロスプラットフォーム対応）"""
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        # プラットフォーム情報を取得
        pinfo = PlatformUtils.get_platform_info()
        
        root = tk.Tk()
        root.withdraw()
        
        # プラットフォーム別の初期ディレクトリ設定
        initial_dir = PlatformUtils.normalize_path("examples")
        if not os.path.exists(initial_dir):
            initial_dir = PlatformUtils.normalize_path(".")
        
        # Windowsの場合はファイルダイアログのスタイルを調整
        if pinfo['is_windows']:
            root.wm_attributes('-topmost', 1)
        
        file_path = filedialog.askopenfilename(
            title=title,
            filetypes=filetypes,
            initialdir=initial_dir
        )
        
        root.destroy()
        return file_path
    except ImportError:
        print("tkinterが利用できません。ファイルパスを直接入力してください。")
        return input(f"{title}: ").strip()

def select_and_execute_file():
    """ファイルダイアログでG-codeまたはSTEPファイルを選択して実行"""
    # プラットフォーム情報を表示
    pinfo = PlatformUtils.get_platform_info()
    platform_name = {
        'windows': 'Windows',
        'darwin': 'macOS', 
        'linux': 'Linux'
    }.get(pinfo['system'], pinfo['system'].title())
    
    print(f"\n=== XYZ Runner (3D) - {platform_name} ===")
    print("G-codeまたはSTEPファイルを選択してください...")
    
    file_path = select_file_with_dialog(
        "G-codeまたはSTEPファイルを選択してください",
        [
            ("G-code files", "*.gcode *.nc *.tap"),
            ("STEP files", "*.stp *.step"), 
            ("All supported", "*.gcode *.nc *.tap *.stp *.step"),
            ("All files", "*.*")
        ]
    )
    
    if not file_path or not os.path.exists(file_path):
        print("ファイルが選択されませんでした。")
        return None, None
    
    # 拡張子から判定
    ext = os.path.splitext(file_path)[1].lower()
    if ext in ['.gcode', '.nc', '.tap']:
        return file_path, "gcode"
    elif ext in ['.stp', '.step']:
        return file_path, "stp"
    else:
        print(f"サポートされていないファイル形式です: {ext}")
        return None, None

def execute_direct_job(g, job_type, file_path):
    """直接ジョブタイプから実行"""
    print(f"実行中: {job_type} ジョブ - {file_path}")
    
    if job_type == "gcode":
        if file_path and os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            for line in lines:
                g.exec(line)
            print(f"G-codeファイル '{file_path}' を実行しました")
        else:
            print(f"G-codeファイル '{file_path}' が見つかりません")
            
    elif job_type == "stp":
        if file_path and os.path.exists(file_path):
            origin = [0, 0, 0]
            resolution = 0.5
            process_step_file_simple(g, file_path, origin, resolution)
            print(f"STEPファイル '{file_path}' を処理しました（簡易モード）")
        else:
            print(f"STEPファイル '{file_path}' が見つかりません")

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
    ap = argparse.ArgumentParser(description="Config-driven XYZ runner (3D)")
    ap.add_argument("--config", help="YAML config path")
    ap.add_argument("--driver", choices=["sim","chuo"])
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--no-animate", action="store_true", help="アニメーション無効化")
    ap.add_argument("--debug", action="store_true", help="[DEBUG]出力を有効化")
    ap.add_argument("--file", help="G-codeまたはSTEPファイルパス")
    args = ap.parse_args()
    # logging はファイル先頭でインポート済み
    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')
    else:
        logging.basicConfig(level=logging.WARNING, format='%(asctime)s [%(levelname)s] %(message)s')
    
    # --- ジョブタイプ選択・実行 ---
    config_path = args.config
    job_type = None
    cfg = None
    
    if not config_path:
        # ファイルダイアログでファイル選択
        file_path, job_type = select_and_execute_file()
        if not file_path:
            print("処理を終了します。")
            return
        
        # 簡易実行用のデフォルト設定を作成
        cfg = {
            "driver": args.driver or "sim",
            "defaults": {"unit": "mm", "mode": "absolute", "feed": 1000},
            "visual": {"show": True, "animate": True, "fps": 1080, "title": "XYZ Runner"},
            "selected_file": file_path  # 選択されたファイルパスを保存
        }
    else:
        # 設定ファイルが指定された場合
        cfg = yaml.safe_load(open(config_path, "r", encoding="utf-8"))
    
    # 設定が未初期化の場合のフォールバック
    if cfg is None:
        cfg = {
            "driver": args.driver or "sim",
            "defaults": {"unit": "mm", "mode": "absolute", "feed": 1000},
            "visual": {"show": True, "animate": True, "fps": 30, "title": "XYZ Runner"}
        }
    
    driver_name = args.driver or cfg.get("driver", "sim")
    if driver_name=="sim":
        drv = SimDriver3D()
    else:
        # 実機用は未実装（必要に応じて拡張）
        drv = SimDriver3D()
    g = GCodeWrapper3D(drv)
    
    # デフォルト設定（単位・座標モード・送り速度）
    d = cfg.get("defaults", {})
    if d.get("unit","mm")=="mm": g.exec("G21")
    else: g.exec("G20")
    if d.get("mode","absolute")=="absolute": g.exec("G90")
    else: g.exec("G91")
    if "feed" in d: g.exec(f"F{float(d['feed'])}")
    
    # ジョブ実行
    if job_type and job_type != "yaml":
        # 直接ジョブタイプ実行
        selected_file = cfg.get("selected_file")
        execute_direct_job(g, job_type, selected_file)
    else:
        # YAML設定からジョブ実行
        for job in cfg.get("jobs", []):
            typ = job["type"]
            print(f"実行中: {typ} ジョブ")
            if typ=="gcode":
                # G-codeファイルの処理
                file_path = job.get("file")
                if not file_path or str(file_path).strip() == "":
                    print("G-codeファイルが指定されていません。")
                    continue
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    for line in lines:
                        g.exec(line)
                    print(f"G-codeファイル '{file_path}' を実行しました")
                else:
                    print(f"G-codeファイル '{file_path}' が見つかりません")
            elif typ=="stp":
                # STEPファイルの処理
                file_path = job.get("file")
                if not file_path or str(file_path).strip() == "":
                    print("STEPファイルが指定されていません。")
                    continue
                if os.path.exists(file_path):
                    origin = job.get("origin", [0, 0, 0])
                    resolution = job.get("resolution", 0.5)
                    # 簡易STEP処理（球体形状の近似）
                    process_step_file_simple(g, file_path, origin, resolution)
                    print(f"STEPファイル '{file_path}' を処理しました（簡易モード）")
                else:
                    print(f"STEPファイル '{file_path}' が見つかりません")
            elif typ=="grid_spheres":
                # 3Dグリッド球体パターンの処理
                origin = job.get("origin", [0, 0, 0])
                area = job.get("area", [100, 100, 50])
                cell = float(job.get("cell", 20))
                sphere_d = float(job.get("sphere_d", 15))
                feed = float(job.get("feed", d.get("feed", 1000)))
                grid_spheres_3d(g, origin, area, cell, sphere_d, feed)
                print(f"3Dグリッド球体パターンを実行しました (cell={cell}mm, sphere_d={sphere_d}mm)")
            else:
                print(f"未対応ジョブタイプ: {typ}")
    
    # ファイル読み込み（コマンドライン引数から）
    if args.file:
        ftype, fdata = load_gcode_or_stp(args.file)
        if ftype=="gcode" and fdata:
            for line in fdata:
                g.exec(line)
            print(f"G-codeファイル '{args.file}' を実行しました")
        elif ftype=="stp":
            print("STEPファイル形状を取得しました（詳細処理は未実装）")
    
    # 軌跡表示
    vis = cfg.get("visual", {})
    show_flag = args.show or bool(vis.get("show", False))
    if show_flag:
        # ファイル名をタイトルに含める
        base_title = vis.get("title", "XYZ Simulation")
        selected_file = cfg.get("selected_file")
        if selected_file:
            filename = os.path.basename(selected_file)
            title = f"{base_title} - {filename}"
        else:
            title = base_title
            
        animate = not args.no_animate and bool(vis.get("animate", True))
        fps = int(vis.get("fps", 30))
        drv.animate_tracks(animate=animate, fps=fps, title=title)
        print("3D軌跡を表示しました")
    else:
        print("軌跡表示をスキップしました（--show または visual.show=true で表示）")

if __name__ == "__main__":
    main()
