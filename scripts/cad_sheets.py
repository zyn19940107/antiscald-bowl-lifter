"""CAD-style engineering drawing sheets (A3) for the raised-handle clip pair + DXF.

Outputs: design/cad/sheet1_assembly.png, sheet2_parts.png, sheet3_details_pot.png,
         design/cad/clips_drawings.pdf, design/cad/clips.dxf
Units: mm.
"""
import math
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle

try:
    import ezdxf
except Exception:
    ezdxf = None

try:
    font_manager.fontManager.addfont('C:/Windows/Fonts/simhei.ttf')
except Exception:
    pass
plt.rcParams['font.family'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

OUT = 'D:/code/vibe/antiscald/design/cad'
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- design data (mm)
R_IN, R_OUT = 62.5, 67.5
WIRE_D = 3.2
WIRE_R = WIRE_D / 2
R_J = 72.5
EYE_MAJOR, EYE_WIRE_R = 7.2, 2.2
EYE_OD = 2 * (EYE_MAJOR + EYE_WIRE_R)
EYE_HOLE = 2 * (EYE_MAJOR - EYE_WIRE_R)
RISER = [(73.5, 1.6), (80.5, 12.5), (87.5, 24.5), (93.0, 34.0), (95.2, 52.0),
         (96.8, 72.0), (99.2, 93.0), (103.8, 112.0), (110.8, 127.0),
         (120.2, 137.0), (131.2, 143.8)]
RISER_D = 6.0
BETA = math.radians(33.0)
HANDLE_LEN = 105.3
HANDLE_W, HANDLE_T = 32.2, 17.0
FERRULE_D, FERRULE_L = 10.0, 22.0
GRIP_U = 55.0
HB = np.array([RISER[-1][0], RISER[-1][1]])
HANDLE_TIP = HB + HANDLE_LEN * np.array([math.cos(BETA), math.sin(BETA)])
HANDLE_ST = [(0.0, 11.5, 6.0), (3.3, 21.8, 10.4), (7.0, 28.8, 13.4), (12.5, 31.2, 14.8),
             (19.0, 29.8, 15.0), (26.0, 31.2, 15.6), (35.5, 32.2, 16.0), (46.5, 31.8, 15.9),
             (58.0, 30.2, 15.3), (69.0, 27.8, 14.4), (79.0, 24.8, 13.2), (87.5, 21.2, 11.6),
             (94.5, 17.2, 9.6), (100.0, 12.2, 7.0), (103.5, 6.8, 4.0), (105.3, 2.6, 1.5)]
CROOK = [(10.11, 0.0), (11.20, 2.2), (12.40, 5.0), (13.40, 8.0), (13.80, 10.2),
         (13.50, 11.8), (12.50, 12.7), (11.00, 12.8), (9.60, 11.8), (8.60, 10.0),
         (8.00, 7.6), (7.70, 5.4), (7.50, 3.9), (6.60, 3.85), (5.80, 3.65),
         (5.00, 3.15), (4.40, 2.35), (3.90, 1.35), (3.42, 0.22), (3.20, -1.30),
         (2.80, -2.60), (2.20, -3.40), (1.60, -3.75), (1.00, -3.70)]
BOWL_PROF = [(0, 0), (30, 0), (38, 2), (44, 6), (50, 13), (55.3, 30), (60.9, 45.4),
             (63.0, 49.5), (65.5, 53.5), (68.7, 57.5), (72.5, 61.5), (76.6, 65.5),
             (80.6, 69.5), (84.1, 73.5), (86.1, 77.0), (86.8, 79.5), (86.0, 82.8)]
POT_R, POT_DEPTH = 120.0, 140.0
POT_ID = 2 * POT_R
RING_Z = 30.0

INK = '#1b1b1b'
GRAY = '#5f5f5f'
BLUE = '#2b4f7a'
RED = '#a03020'
LW_T, LW_M, LW_H = 0.4, 0.65, 0.95


# ---------------------------------------------------------------- geometry helpers
def ring_wire_path(kind, radius, n=240):
    a0, a1 = (math.radians(262.0), math.radians(98.0)) if kind == 'eye' else \
             (math.radians(-82.0), math.radians(82.0))
    u = np.linspace(0, 1, n)
    ang = a0 + (a1 - a0) * u
    f = np.clip(np.exp(-((u / 0.075) ** 2)) + np.exp(-(((1 - u) / 0.075) ** 2)), 0, 1)
    r = radius + (R_J - radius) * f
    return np.stack([r * np.cos(ang), r * np.sin(ang)], axis=1)


def handle_outline_elev(side):
    base = np.array([side * HB[0], HB[1]])
    ax = np.array([side * math.cos(BETA), math.sin(BETA)])
    pe = np.array([-ax[1], ax[0]])
    top, bot = [], []
    for (u, w, t) in HANDLE_ST:
        c = base + u * ax
        top.append(c + (t / 2 + 0.4) * pe)
        bot.append(c - (t / 2 + 0.4) * pe)
    return np.array(top), np.array(bot), base + (HANDLE_LEN + 1.0) * ax, ax, pe


def handle_outline_plan(side):
    x0 = side * RISER[-1][0]
    s = side * math.cos(BETA)
    top, bot = [], []
    for (u, w, t) in HANDLE_ST:
        x = x0 + s * u
        top.append((x, w / 2 + 0.4))
        bot.append((x, -w / 2 - 0.4))
    return np.array(top), np.array(bot), np.array([x0 + s * (HANDLE_LEN + 1.0), 0.0])


def make_T(real_bbox, sheet_box, pad=10, snaps=(0.5, 0.4, 0.33, 0.25, 0.2)):
    x0, y0, x1, y1 = real_bbox
    a, b, c, d = sheet_box
    sc = min((c - a - 2 * pad) / max(x1 - x0, 1e-6), (d - b - 2 * pad) / max(y1 - y0, 1e-6))
    pick = sc
    for s in snaps:
        if s <= sc:
            pick = s
            break
    rcx, rcy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    ccx, ccy = (a + c) / 2.0, (b + d) / 2.0

    def T(p):
        return (ccx + (p[0] - rcx) * pick, ccy + (p[1] - rcy) * pick)
    return T, pick


# ---------------------------------------------------------------- sheet class
class Sheet:
    def __init__(self, title, no, scale):
        self.fig = plt.figure(figsize=(16.54, 11.69))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, 420)
        self.ax.set_ylim(0, 297)
        self.ax.axis('off')
        self.ax.set_aspect('equal')
        self.ax.add_patch(Rectangle((10, 10), 400, 277, fill=False, ec=INK, lw=0.9))
        self.ax.add_patch(Rectangle((12, 12), 396, 273, fill=False, ec=INK, lw=0.3))
        self._titleblock(title, no, scale)

    def _titleblock(self, title, no, scale):
        x0, y0, w, h = 222, 12, 186, 38
        self.ax.add_patch(Rectangle((x0, y0), w, h, fill=False, ec=INK, lw=0.6))
        self.line([(x0, y0 + 25), (x0 + w, y0 + 25)], lw=0.45)
        self.line([(x0, y0 + 12), (x0 + w, y0 + 12)], lw=0.45)
        for xx in (x0 + 118, x0 + 156):
            self.line([(xx, y0), (xx, y0 + 25)], lw=0.4)
        self.text((x0 + 3, y0 + 31), title, 7.6, INK)
        self.text((x0 + 121, y0 + 31), '图号 ' + no, 6.2, GRAY)
        self.text((x0 + 159, y0 + 31), '比例 ' + scale, 6.2, GRAY)
        self.text((x0 + 3, y0 + 18), '材料：304 不锈钢 / 工程塑料', 6.2, GRAY)
        self.text((x0 + 121, y0 + 18), '单位 mm', 6.2, GRAY)
        self.text((x0 + 159, y0 + 18), '版次 V2', 6.2, GRAY)
        self.text((x0 + 3, y0 + 5), '设计：AI 辅助', 6.2, GRAY)
        self.text((x0 + 121, y0 + 5), '日期 2026-07', 6.2, GRAY)
        self.text((x0 + 159, y0 + 5), '张次 1/1', 6.2, GRAY)

    def line(self, pts, lw=LW_T, color=INK, ls='-'):
        pts = np.asarray(pts, float)
        self.ax.plot(pts[:, 0], pts[:, 1], lw=lw, color=color, ls=ls,
                     solid_capstyle='round', solid_joinstyle='round')

    def circle(self, c, r, lw=LW_T, color=INK, fill=None):
        self.ax.add_patch(plt.Circle(c, r, fill=fill is not None, fc=fill, ec=color, lw=lw))

    def text(self, xy, s, size=7.0, color=INK, ha='left', va='center'):
        self.ax.text(xy[0], xy[1], s, fontsize=size, color=color, ha=ha, va=va)

    def centerline(self, pts, color=GRAY):
        pts = np.asarray(pts, float)
        self.ax.plot(pts[:, 0], pts[:, 1], lw=0.35, color=color, ls=(0, (9, 3, 2, 3)))

    def dim_h(self, x1, x2, y, label, size=6.0, off=1.8, ext=1.8):
        if x2 < x1:
            x1, x2 = x2, x1
        self.line([(x1, y - ext), (x1, y + ext)], lw=LW_T, color=GRAY)
        self.line([(x2, y - ext), (x2, y + ext)], lw=LW_T, color=GRAY)
        self.ax.annotate('', xy=(x1, y), xytext=(x2, y),
                         arrowprops=dict(arrowstyle='<->', color=GRAY, lw=0.5,
                                         shrinkA=0, shrinkB=0))
        self.text(((x1 + x2) / 2, y + off), label, size, GRAY, ha='center')

    def dim_v(self, y1, y2, x, label, size=6.0, off=1.8, ext=1.8):
        if y2 < y1:
            y1, y2 = y2, y1
        self.line([(x - ext, y1), (x + ext, y1)], lw=LW_T, color=GRAY)
        self.line([(x - ext, y2), (x + ext, y2)], lw=LW_T, color=GRAY)
        self.ax.annotate('', xy=(x, y1), xytext=(x, y2),
                         arrowprops=dict(arrowstyle='<->', color=GRAY, lw=0.5,
                                         shrinkA=0, shrinkB=0))
        self.text((x + off, (y1 + y2) / 2), label, size, GRAY, ha='left')

    def leader(self, xy, xytext, label, size=6.0, ha='left'):
        self.ax.annotate(label, xy=xy, xytext=xytext, fontsize=size, color=INK, ha=ha,
                         va='center', arrowprops=dict(arrowstyle='-|>', color=GRAY,
                                                      lw=0.5, shrinkA=0.5, shrinkB=0.5))

    def vtitle(self, xy, s, size=7.8):
        self.text(xy, s, size, INK, ha='center')

    def save(self, name, pdf):
        p = os.path.join(OUT, name)
        self.fig.savefig(p, dpi=220, facecolor='white')
        pdf.savefig(self.fig, facecolor='white')
        print('[cad] wrote', p)
        plt.close(self.fig)


# ---------------------------------------------------------------- view drawers
def draw_ring(sh, T, kind):
    for rad in (R_IN, R_OUT):
        sh.line([T(p) for p in ring_wire_path(kind, rad)], lw=LW_H)


def draw_eyes(sh, T, sc, kind):
    for ey in (-R_J, R_J):
        if kind == 'eye':
            c = T((0, ey))
            sh.circle(c, EYE_OD / 2 * sc, lw=LW_M)
            sh.circle(c, EYE_HOLE / 2 * sc, lw=LW_M)
            sh.circle(c, EYE_MAJOR * sc, lw=0.3, color=GRAY)
        else:
            s = 1 if ey > 0 else -1
            d = np.array([0.9975, -0.0702 * s])
            pts = [T((0, ey) + np.array([u * d[0], u * d[1] * s])) for (u, z) in CROOK[::2]]
            sh.line(pts, lw=LW_M, color=BLUE)


def draw_top_pair(sh, T, sc):
    for kind in ('eye', 'hook'):
        draw_ring(sh, T, kind)
    for ey in (-R_J, R_J):
        c = T((0, ey))
        sh.circle(c, EYE_OD / 2 * sc, lw=LW_M)
        sh.circle(c, EYE_HOLE / 2 * sc, lw=LW_M)
    for side in (-1, 1):
        sh.line([T((side * 73.5, 0)), T((side * RISER[-1][0], 0))], lw=1.2)
        top, bot, tip = handle_outline_plan(side)
        pts = [T(p) for p in top] + [T(tip)] + [T(p) for p in reversed(bot)]
        sh.line(pts + [pts[0]], lw=LW_M)


def draw_top_clip(sh, T, sc, kind):
    side = -1 if kind == 'eye' else 1
    draw_ring(sh, T, kind)
    draw_eyes(sh, T, sc, kind)
    a1 = T((side * R_IN, 9.2 * (1 if side < 0 else -1)))
    a2 = T((side * R_OUT, -8.7 * (1 if side < 0 else -1)))
    apex = T((side * 73.5, 0))
    sh.line([a1, apex, a2], lw=LW_M)
    sh.line([apex, T((side * RISER[-1][0], 0))], lw=1.2)
    sh.line([T((side * (RISER[-1][0] - 9), 0)), T((side * (RISER[-1][0] + 9), 0))],
            lw=2.0, color=GRAY)
    top, bot, tip = handle_outline_plan(side)
    pts = [T(p) for p in top] + [T(tip)] + [T(p) for p in reversed(bot)]
    sh.line(pts + [pts[0]], lw=LW_M)


def draw_handle_elev(sh, T, sc, side):
    for xx in (R_IN, R_OUT):
        sh.circle(T((side * xx, 0.0)), WIRE_D / 2 * sc, lw=LW_M, fill='white')
    sh.line([T((side * R_IN, 0)), T((side * 73.5, 1.6)), T((side * R_OUT, 0))], lw=LW_M)
    rr = [T((side * rho, z)) for (rho, z) in RISER]
    sh.line(rr, lw=1.4)
    sh.centerline(rr)
    base = np.array([side * HB[0], HB[1]])
    axv = np.array([side * math.cos(BETA), math.sin(BETA)])
    pv = np.array([-axv[1], axv[0]])
    f0 = base - axv * (FERRULE_L / 2)
    f1 = base + axv * (FERRULE_L / 2)
    quad = [f0 + pv * FERRULE_D / 2, f1 + pv * FERRULE_D / 2,
            f1 - pv * FERRULE_D / 2, f0 - pv * FERRULE_D / 2]
    sh.line([T(p) for p in quad] + [T(quad[0])], lw=LW_M)
    top, bot, tip, _, _ = handle_outline_elev(side)
    sh.line([T(p) for p in top], lw=LW_M)
    sh.line([T(p) for p in bot], lw=LW_M)
    sh.line([T(top[-1]), T(tip), T(bot[-1])], lw=LW_M)
    g = HB * np.array([side, 1.0]) + GRIP_U * np.array([side * math.cos(BETA), math.sin(BETA)])
    sh.line([T(g + 7 * pv), T(g - 7 * pv)], lw=LW_M, color=BLUE)


# ---------------------------------------------------------------- sheet 1
def sheet1(pdf):
    sh = Sheet('双夹联锁取碗夹（加高把手版）—— 总装图', 'ASSY-01', '1:2.5')
    T, sc = make_T((-232, -18, 232, 212), (16, 148, 236, 282))
    sh.line([T((-69.1, 0)), T((69.1, 0))], lw=2.2)
    sh.circle(T((0, 0)), EYE_OD / 2 * sc, lw=LW_M)
    sh.circle(T((0, 0)), EYE_HOLE / 2 * sc, lw=LW_M)
    for side in (-1, 1):
        sh.line([T((side * R_IN, 0)), T((side * 73.5, 1.6)), T((side * R_OUT, 0))], lw=LW_M)
        sh.line([T((side * rho, z)) for (rho, z) in RISER], lw=1.3)
        base = np.array([side * HB[0], HB[1]])
        axv = np.array([side * math.cos(BETA), math.sin(BETA)])
        pv = np.array([-axv[1], axv[0]])
        f0 = base - axv * (FERRULE_L / 2)
        f1 = base + axv * (FERRULE_L / 2)
        quad = [f0 + pv * FERRULE_D / 2, f1 + pv * FERRULE_D / 2,
                f1 - pv * FERRULE_D / 2, f0 - pv * FERRULE_D / 2]
        sh.line([T(p) for p in quad] + [T(quad[0])], lw=LW_M)
        top, bot, tip, _, _ = handle_outline_elev(side)
        sh.line([T(p) for p in top], lw=LW_M)
        sh.line([T(p) for p in bot], lw=LW_M)
        sh.line([T(top[-1]), T(tip), T(bot[-1])], lw=LW_M)
    sh.centerline([T((-HANDLE_TIP[0] - 15, 0)), T((HANDLE_TIP[0] + 15, 0))])
    sh.vtitle((126, 282), 'A — A   正视（两夹合围，拆去碗）')
    y0 = T((0, 0))[1]
    sh.dim_v(y0, T((0, HANDLE_TIP[1]))[1], 26, '总高 %.1f' % HANDLE_TIP[1])
    sh.dim_v(y0, T((0, HB[1]))[1], 38, '立管高 %.0f' % HB[1])
    sh.dim_h(T((-HANDLE_TIP[0], 0))[0], T((HANDLE_TIP[0], 0))[0], y0 - 14,
             '把手总跨距 %.0f' % (2 * HANDLE_TIP[0]))
    sh.leader(T((0, 0)), (86, 132), '孔 / 钩互锁关节  眼环 φ%.1f / 孔 φ%.0f' % (EYE_OD, EYE_HOLE), 6.0)
    sh.leader(T((-150, 96)), (58, 152), '把手仰角 33°', 6.2)
    T2, sc2 = make_T((-232, -92, 232, 92), (16, 66, 236, 148), pad=8)
    draw_top_pair(sh, T2, sc2)
    sh.vtitle((126, 152), 'B — B   俯视（两夹合围）')
    sh.dim_h(T2((-69.1, 0))[0], T2((69.1, 0))[0], T2((0, 0))[1] - 13,
             '钢环外径 φ%.1f' % (2 * (R_OUT + WIRE_R)))
    sh.dim_v(T2((0, -R_J))[1], T2((0, R_J))[1], T2((-196, 0))[0], '两端中心距 %.0f' % (2 * R_J))
    sh.leader(T2((0, R_J)), (120, 140), '孔（眼环）φ%.1f，与钩互锁' % EYE_OD, 6.0)
    sh.leader(T2((-150, 0)), (150, 80), '加高把手（俯视投影）', 6.0)
    ref = 'D:/code/vibe/antiscald/design/v2_clip_pair.png'
    if os.path.exists(ref):
        sh.ax.imshow(plt.imread(ref), extent=(248, 402, 198, 286), aspect='auto', zorder=0)
        sh.ax.add_patch(Rectangle((248, 198), 154, 88, fill=False, ec=INK, lw=0.5))
        sh.text((251, 202), '3D 参考图', 6.0, GRAY)
    x0, y0b = 248, 118
    sh.text((x0, y0b + 74), '明细表', 8.0, INK)
    rows = [('序号', '名称', '数量', '材料 / 规格'),
            ('1', '孔夹（A）', '1', '304 弹簧钢丝 φ3.2'),
            ('2', '钩夹（B）', '1', '304 弹簧钢丝 φ3.2'),
            ('3', '立管', '2', '304 管 φ6×0.8'),
            ('4', '手柄', '2', '原鱼形手柄（塑料）'),
            ('5', '卡箍', '2', '304 管 φ10×22'),
            ('6', 'V 形支架', '2', '304 钢丝 φ3.2')]
    yy = y0b + 66
    for i, r in enumerate(rows):
        sh.text((x0 + 2, yy), r[0], 6.2)
        sh.text((x0 + 16, yy), r[1], 6.2)
        sh.text((x0 + 92, yy), r[2], 6.2)
        sh.text((x0 + 108, yy), r[3], 6.2)
        if i == 0:
            sh.line([(x0, yy - 4.5), (x0 + 152, yy - 4.5)], lw=0.35)
        yy -= 8.2
    sh.line([(x0, y0b + 60), (x0, yy + 12)], lw=0.35)
    sh.line([(x0 + 152, y0b + 60), (x0 + 152, yy + 12)], lw=0.35)
    notes = ['技术要求：',
             '1. 两夹除端头（孔 / 钩）外尺寸相同，左右各一件成套使用。',
             '2. 钢圈：304 弹簧钢丝 φ3.2 冷弯；眼环 / 弯钩与钢圈钎焊（银钎料），去应力处理。',
             '3. 立管 φ6×0.8 与 V 形支架、卡箍焊接；焊缝打磨，整体电解抛光。',
             '4. 手柄与卡箍：环氧结构胶 + 横向销钉固定，可更换原厂手柄。',
             '5. 合围后孔环内径 φ121.8；钩尖与孔壁单边间隙 0.5~1 mm，加载后自动贴紧。',
             '6. 适用：碗口 φ≥150、碗身在夹持高度之上向外扩；锅口内径 ≥240（详见 DETAIL-03）。']
    yy = 56
    for i, s in enumerate(notes):
        sh.text((18, yy), s, 6.4 if i else 7.0, INK if i == 0 else GRAY)
        yy -= 5.0
    sh.save('sheet1_assembly.png', pdf)


# ---------------------------------------------------------------- sheet 2
def sheet2(pdf):
    sh = Sheet('孔夹 / 钩夹 —— 零件图', 'PART-02', '1:2')
    T, sc = make_T((-235, -90, 78, 90), (16, 176, 208, 282), pad=8)
    draw_top_clip(sh, T, sc, 'eye')
    sh.vtitle((112, 282), '孔夹（A）—— 俯视')
    sh.dim_h(T((-69.1, 0))[0], T((69.1, 0))[0], T((0, 0))[1] - 14,
             'φ%.1f' % (2 * (R_OUT + WIRE_R)))
    sh.dim_v(T((0, -R_J))[1], T((0, R_J))[1], T((84, 0))[0], '两端中心距 %.0f' % (2 * R_J))
    sh.leader(T((0, R_J)), (118, 270),
              '眼环：外径 φ%.1f，孔 φ%.0f，环丝 φ%.1f' % (EYE_OD, EYE_HOLE, 2 * EYE_WIRE_R), 6.0)
    sh.leader(T((-R_IN * math.cos(math.radians(35)), R_IN * math.sin(math.radians(35)))),
              (120, 204), '双钢丝 φ3.2  中心线 R62.5 / R67.5', 6.0)
    sh.leader(T((-165, 0)), (24, 168), '鱼形手柄 105×32×17（原手柄）', 6.0)
    T2, sc2 = make_T((-235, -16, 8, 212), (16, 62, 208, 168), pad=8)
    draw_handle_elev(sh, T2, sc2, -1)
    sh.vtitle((112, 172), '孔夹（A）—— 手柄侧视（真实形状）')
    sh.dim_v(T2((0, 0))[1], T2((0, HANDLE_TIP[1]))[1], 22, '总高 %.1f' % HANDLE_TIP[1])
    sh.dim_h(T2((0, 0))[0], T2((-HANDLE_TIP[0], 0))[0], T2((0, 0))[1] - 10,
             '%.1f' % HANDLE_TIP[0])
    sh.leader(T2((-100, 110)), (118, 152), '立管 φ6×0.8  弯曲半径 ≥60（坐标见右表）', 6.0)
    sh.leader(T2((-HB[0], HB[1])), (118, 130), '卡箍 φ10×22', 6.0)
    sh.leader(T2((-65, 0)), (118, 110), 'V 形支架（原 φ3.2）', 6.0)
    T3, sc3 = make_T((-78, -90, 235, 90), (238, 176, 404, 282), pad=8)
    draw_top_clip(sh, T3, sc3, 'hook')
    sh.vtitle((321, 282), '钩夹（B）—— 俯视（仅端头不同）')
    sh.leader(T3((0, R_J)), (300, 266), '弯钩（详见 DETAIL-03）', 6.0)
    tx, ty = 244, 158
    sh.text((tx, ty + 5), '立管中心线坐标（R 距环心，Z 距环平面）', 6.4, INK)
    sh.line([(tx, ty), (tx + 158, ty)], lw=0.35)
    for i, (rho, z) in enumerate(RISER):
        col, row = i % 2, i // 2
        xx = tx + 6 + col * 80
        yy = ty - 11 - row * 8.6
        sh.text((xx, yy), 'P%d' % (i + 1), 5.8, GRAY)
        sh.text((xx + 18, yy), 'R %.1f' % rho, 5.8, GRAY)
        sh.text((xx + 52, yy), 'Z %.1f' % z, 5.8, GRAY)
    sh.text((tx, ty - 11 - 6 * 8.6 - 4), '展开长 ≈159 mm（两端另留修配余量）', 5.8, GRAY)
    sh.text((tx, ty - 11 - 6 * 8.6 - 12), '材料：304 管 φ6×0.8；弯曲圆角 ≥60，端部压扁 20 长', 5.8, GRAY)
    notes = ['技术要求：',
             '1. 材料：304 不锈钢弹簧钢丝 φ3.2（GB/T 24588），冷弯成型后去应力处理。',
             '2. 圆环两股钢丝中心线半径 R62.5 / R67.5，各 180°；端头并拢至 R72.5 后成型。',
             '3. 眼环：外径 φ18.8，孔 φ10，环丝 φ4.4，末端并焊；弯钩线径 φ3.2（见 DETAIL-03）。',
             '4. 各弯曲圆角 ≥1.5×线径；焊接部位打磨、抛光；整体电解抛光。']
    yy = 56
    for i, s in enumerate(notes):
        sh.text((18, yy), s, 6.4 if i else 7.0, INK if i == 0 else GRAY)
        yy -= 5.0
    sh.save('sheet2_parts.png', pdf)


# ---------------------------------------------------------------- sheet 3
def sheet3(pdf):
    sh = Sheet('端头细节 · 装配间隙 · 锅具适配', 'DETAIL-03', '见图')
    T, sc = make_T((-18, -14, 12, 12), (18, 205, 118, 283), pad=8, snaps=(2.5, 2.0, 1.5, 1.0))
    sh.circle(T((0, 0)), EYE_OD / 2 * sc, lw=LW_H)
    sh.circle(T((0, 0)), EYE_HOLE / 2 * sc, lw=LW_H)
    sh.circle(T((0, 0)), EYE_MAJOR * sc, lw=0.3, color=GRAY)
    sh.line([T((-16.5, -2.6)), T((-11.5, -1.4)), T((-10.1, 0.7)), T((-4.5, -5.6)), T((0, -7.2))], lw=LW_M)
    sh.line([T((-16.5, 2.6)), T((-11.5, 1.4)), T((-10.1, 0.7))], lw=LW_M)
    sh.vtitle((68, 282), 'DETAIL A  眼环（孔）俯视', 7.4)
    sh.dim_h(T((-EYE_HOLE / 2, 0))[0], T((EYE_HOLE / 2, 0))[0], T((0, 0))[1] - 20, 'φ%.0f' % EYE_HOLE)
    sh.dim_h(T((-EYE_OD / 2, 0))[0], T((EYE_OD / 2, 0))[0], T((0, 0))[1] - 28, 'φ%.1f' % EYE_OD)
    sh.leader(T((0, EYE_MAJOR)), (82, 274), '环丝 φ%.1f' % (2 * EYE_WIRE_R), 5.8)
    sh.leader(T((-10.1, 0.7)), (26, 212), '两股钢丝并拢→收成环丝，末端钎焊', 5.8)
    T2, sc2 = make_T((-17, -8, 18, 19), (128, 205, 262, 283), pad=8, snaps=(2.5, 2.0, 1.5, 1.0))
    sh.circle(T2((-EYE_MAJOR, 0)), EYE_WIRE_R * sc2, lw=LW_M, fill='white')
    sh.circle(T2((EYE_MAJOR, 0)), EYE_WIRE_R * sc2, lw=LW_M, fill='white')
    sh.line([T2((u, z)) for (u, z) in CROOK], lw=LW_H)
    sh.vtitle((195, 282), 'DETAIL B  弯钩 + 眼环（剖面）', 7.4)
    sh.dim_v(T2((0, 0))[1], T2((0, 12.8))[1], T2((16.5, 0))[0], '钩顶 15.0')
    sh.dim_v(T2((0, -3.75))[1], T2((0, 0))[1], T2((-16.5, 0))[0], '钩尖下探 3.8')
    sh.dim_h(T2((-EYE_MAJOR, 0))[0], T2((EYE_MAJOR, 0))[0], T2((0, 0))[1] - 20,
             '眼环中心距 %.1f' % (2 * EYE_MAJOR))
    sh.leader(T2((13.8, 10.2)), (214, 270), '钩顶圆弧 R≈4.5，线径 φ3.2', 5.8)
    T3, sc3 = make_T((-24, -8, 26, 14), (272, 205, 402, 283), pad=8, snaps=(2.5, 2.0, 1.5, 1.0))
    sh.circle(T3((-EYE_MAJOR, 0)), EYE_WIRE_R * sc3, lw=LW_M, fill='white')
    sh.circle(T3((EYE_MAJOR, 0)), EYE_WIRE_R * sc3, lw=LW_M, fill='white')
    sh.line([T3((u, z)) for (u, z) in CROOK], lw=LW_H)
    sh.ax.annotate('', xy=T3((-19, 0)), xytext=T3((-27, 0)),
                   arrowprops=dict(arrowstyle='-|>', color=RED, lw=1.0))
    sh.ax.annotate('', xy=T3((27, 3.5)), xytext=T3((19, 3.5)),
                   arrowprops=dict(arrowstyle='-|>', color=RED, lw=1.0))
    sh.text(T3((-28.5, 2)), 'T', 7.4, RED)
    sh.text(T3((26.5, 5.6)), 'T', 7.4, RED)
    sh.vtitle((337, 282), 'DETAIL C  钩孔自锁受力', 7.4)
    sh.text((337, 196), '碗重→环向拉力 T→钩尖压孔壁、钩颈搭孔环上表面；越重越锁紧。', 5.8, GRAY, ha='center')
    T4, sc4 = make_T((-250, -12, 135, 235), (18, 66, 232, 188), pad=8, snaps=(0.5, 0.4, 0.33))
    pot = [(-POT_R, 0), (-POT_R + 5, 0), (-POT_R, 6), (-POT_R, POT_DEPTH),
           (-POT_R - 4, POT_DEPTH + 2), (-POT_R - 4, POT_DEPTH - 1), (-POT_R - 3, 6),
           (-POT_R + 2, -3), (POT_R - 2, -3), (POT_R + 3, 6), (POT_R + 4, POT_DEPTH - 1),
           (POT_R + 4, POT_DEPTH + 2), (POT_R, POT_DEPTH), (POT_R, 6), (POT_R - 5, 0),
           (POT_R, 0)]
    sh.line([T4(p) for p in pot], lw=LW_M)
    sh.line([T4((r, z)) for (r, z) in BOWL_PROF], lw=LW_M, color=BLUE)
    sh.line([T4((-r, z)) for (r, z) in BOWL_PROF], lw=LW_M, color=BLUE)
    for side in (-1, 1):
        zc = RING_Z
        for rr in (R_IN, R_OUT):
            sh.circle(T4((side * rr, zc)), WIRE_D / 2 * sc4, lw=LW_M, fill='white')
        sh.line([T4((side * R_IN, zc)), T4((side * 73.5, zc + 1.6)), T4((side * R_OUT, zc))], lw=LW_M)
        sh.line([T4((side * rho, zc + z)) for (rho, z) in RISER], lw=1.2)
        top, bot, tip, _, _ = handle_outline_elev(side)
        sh.line([T4((p[0], zc + p[1])) for p in top], lw=LW_M)
        sh.line([T4((p[0], zc + p[1])) for p in bot], lw=LW_M)
    sh.vtitle((125, 192), '锅具适配剖面（参考：锅口 φ240 / 深 140 / 碗口 φ173）', 7.4)
    sh.dim_v(T4((0, 0))[1], T4((0, POT_DEPTH))[1], T4((-POT_R - 16, 0))[0], '锅深 %.0f' % POT_DEPTH)
    sh.dim_h(T4((-POT_R, 0))[0], T4((POT_R, 0))[0], T4((0, 0))[1] - 12, '锅口内径 φ%.0f' % POT_ID)
    sh.dim_v(T4((0, POT_DEPTH))[1], T4((0, RING_Z + HANDLE_TIP[1]))[1],
             T4((POT_R + 26, 0))[0], '把手尖端高出锅沿 %.0f' % (RING_Z + HANDLE_TIP[1] - POT_DEPTH))
    sh.leader(T4((-POT_R, POT_DEPTH - 6)), (46, 74), '立管在锅沿高度处距锅壁 ≥%.0f mm' % (POT_R - 104), 5.8)
    sh.leader(T4((-55.3, RING_Z)), (120, 106), '钢环在碗腰处楔紧（环平面距锅底约 30）', 5.8)
    tx, ty = 248, 188
    sh.text((tx, ty + 4), '锅具适配表（碗坐锅底，环平面距锅底 ≈30）', 6.4, INK)
    rows = [('锅口内径', '建议最大锅深', '把手高出锅沿'),
            ('≥ φ220', '≈ 120', '≈ 60'),
            ('≥ φ240', '≈ 140', '≈ 45'),
            ('≥ φ260', '≈ 160', '≈ 30')]
    for i, r in enumerate(rows):
        yy = ty - 8 - i * 9
        for j, s in enumerate(r):
            sh.text((tx + 3 + j * 52, yy), s, 6.0, GRAY if i else INK)
    use = ['使用（锅中取碗）：',
           '1. 手持加高把手，将孔夹 U 环从锅口上方压入，套过碗沿落在碗腰；同法放入钩夹；',
           '2. 两夹端头对齐，钩夹下放，两个钩尖落入眼环；',
           '3. 双手同时上提加高把手：钢环楔紧、碗被锁住，提过锅口后移出；',
           '4. 放碗后下松把手卸载，上提钩夹、两夹向两侧退出。']
    yy = 140
    for i, s in enumerate(use):
        sh.text((248, yy), s, 6.2 if i else 6.8, INK if i == 0 else GRAY)
        yy -= 5.4
    notes = ['注：', '1. 把手加高后，手部在锅沿以上操作，锅壁不再阻挡。',
             '2. 锅更深/更窄时按 R-Z 坐标表延长立管，或选用加长立管版本。']
    yy = 56
    for i, s in enumerate(notes):
        sh.text((18, yy), s, 6.2 if i else 6.6, INK if i == 0 else GRAY)
        yy -= 5.0
    sh.save('sheet3_details_pot.png', pdf)


# ---------------------------------------------------------------- DXF
def write_dxf():
    if ezdxf is None:
        print('[cad] ezdxf missing, skip DXF')
        return
    doc = ezdxf.new('R2010', setup=True)
    doc.header['$INSUNITS'] = 4
    msp = doc.modelspace()
    for name, col in (('U-RING', 7), ('JOINT', 1), ('HANDLE', 3), ('RISER', 4), ('TEXT', 2)):
        doc.layers.add(name, color=col)

    def pl(pts, layer):
        msp.add_lwpolyline([(float(x), float(y)) for (x, y) in pts], close=False,
                           dxfattribs={'layer': layer})

    for kind in ('eye', 'hook'):
        for rad in (R_IN, R_OUT):
            pl(ring_wire_path(kind, rad), 'U-RING')
    for ey in (-R_J, R_J):
        msp.add_circle((0, ey), EYE_OD / 2, dxfattribs={'layer': 'JOINT'})
        msp.add_circle((0, ey), EYE_HOLE / 2, dxfattribs={'layer': 'JOINT'})
        s = 1 if ey > 0 else -1
        d = np.array([0.9975, -0.0702 * s])
        pl([(u * d[0], ey + u * d[1] * s) for (u, z) in CROOK], 'JOINT')
    for side in (-1, 1):
        pl([(side * 73.5, 0), (side * RISER[-1][0], 0)], 'RISER')
        top, bot, tip = handle_outline_plan(side)
        pl(list(top) + [tuple(tip)] + list(bot)[::-1] + [tuple(top[0])], 'HANDLE')
    msp.add_text('TOP VIEW - assembled pair (unit mm, 1:1)',
                 dxfattribs={'layer': 'TEXT', 'height': 6}).set_placement((-70, 108))
    off_y = -260
    for xx in (R_IN, R_OUT):
        msp.add_circle((-xx, off_y), WIRE_D / 2, dxfattribs={'layer': 'U-RING'})
    pl([(-R_IN, off_y), (-73.5, off_y + 1.6), (-R_OUT, off_y)], 'U-RING')
    pl([(-rho, off_y + z) for (rho, z) in RISER], 'RISER')
    base = np.array([-HB[0], off_y + HB[1]])
    axv = np.array([-math.cos(BETA), math.sin(BETA)])
    pv = np.array([-axv[1], axv[0]])
    f0 = base - axv * (FERRULE_L / 2)
    f1 = base + axv * (FERRULE_L / 2)
    quad = [f0 + pv * FERRULE_D / 2, f1 + pv * FERRULE_D / 2,
            f1 - pv * FERRULE_D / 2, f0 - pv * FERRULE_D / 2]
    pl([tuple(p) for p in quad] + [tuple(quad[0])], 'HANDLE')
    top, bot, tip, _, _ = handle_outline_elev(-1)
    pts = [(p[0], p[1] + off_y) for p in top] + [(tip[0], tip[1] + off_y)] + \
          [(p[0], p[1] + off_y) for p in bot[::-1]] + [(top[0][0], top[0][1] + off_y)]
    pl(pts, 'HANDLE')
    msp.add_text('HANDLE ELEVATION (true shape, unit mm)',
                 dxfattribs={'layer': 'TEXT', 'height': 6}).set_placement((-220, off_y + 222))
    dx, dy = 330, -60
    msp.add_circle((dx, dy), EYE_OD / 2, dxfattribs={'layer': 'JOINT'})
    msp.add_circle((dx, dy), EYE_HOLE / 2, dxfattribs={'layer': 'JOINT'})
    pl([(dx + u, dy + z) for (u, z) in CROOK], 'JOINT')
    msp.add_text('DETAIL: eye (top view) + hook (front section)',
                 dxfattribs={'layer': 'TEXT', 'height': 6}).set_placement((dx - 40, dy + 24))
    path = os.path.join(OUT, 'clips.dxf')
    doc.saveas(path)
    print('[cad] wrote', path)


def main():
    pdf_path = os.path.join(OUT, 'clips_drawings.pdf')
    with PdfPages(pdf_path) as pdf:
        sheet1(pdf)
        sheet2(pdf)
        sheet3(pdf)
    print('[cad] pdf:', pdf_path)
    write_dxf()


if __name__ == '__main__':
    main()
