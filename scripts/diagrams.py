"""Generate 2D explanatory diagrams for the design sheet (matplotlib -> PNG)."""
import math
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.patches import Annulus, Circle, Polygon, FancyArrowPatch

for fp in ('C:/Windows/Fonts/simhei.ttf', 'C:/Windows/Fonts/msyh.ttc'):
    try:
        font_manager.fontManager.addfont(fp)
    except Exception:
        pass
plt.rcParams['font.family'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

OUT = 'D:/code/vibe/antiscald/design'
os.makedirs(OUT, exist_ok=True)

WIRE_R = 0.0016
R_IN = 0.0625
R_OUT = 0.0675
R_J = 0.0725
EYE_MAJOR = 0.0072
EYE_LOOP_R = 0.0022
CONTACT_Z = 0.0454

BOWL_OUTER = [
    (0.0000, 0.0000), (0.0130, 0.0000), (0.0235, 0.0000), (0.0298, 0.0006),
    (0.0345, 0.0022), (0.0390, 0.0052), (0.0432, 0.0095), (0.0472, 0.0148),
    (0.0512, 0.0208), (0.0545, 0.0270), (0.0570, 0.0330), (0.0585, 0.0380),
    (0.0600, 0.0420), (0.0612, 0.0455), (0.0630, 0.0495), (0.0655, 0.0535),
    (0.0687, 0.0575), (0.0725, 0.0615), (0.0766, 0.0655), (0.0806, 0.0695),
    (0.0841, 0.0735), (0.0861, 0.0770), (0.0868, 0.0795), (0.0863, 0.0812),
    (0.0846, 0.0824), (0.0830, 0.0828), (0.0808, 0.0820),
]
BOWL_INNER = [
    (0.0794, 0.0808), (0.0772, 0.0786), (0.0740, 0.0748), (0.0705, 0.0708),
    (0.0668, 0.0666), (0.0632, 0.0628), (0.0595, 0.0588), (0.0558, 0.0548),
    (0.0522, 0.0508), (0.0488, 0.0468), (0.0452, 0.0428), (0.0418, 0.0388),
    (0.0385, 0.0348), (0.0350, 0.0308), (0.0315, 0.0268), (0.0278, 0.0228),
    (0.0240, 0.0188), (0.0198, 0.0150), (0.0150, 0.0118), (0.0090, 0.0092),
    (0.0040, 0.0078), (0.0000, 0.0074),
]
HANDLE_STATIONS = [
    (0.0835, 0.0115), (0.0868, 0.0218), (0.0905, 0.0288), (0.0960, 0.0312),
    (0.1025, 0.0298), (0.1095, 0.0312), (0.1190, 0.0322), (0.1300, 0.0318),
    (0.1415, 0.0302), (0.1525, 0.0278), (0.1625, 0.0248), (0.1710, 0.0212),
    (0.1780, 0.0172), (0.1835, 0.0122), (0.1870, 0.0068), (0.1888, 0.0026),
]
CROOK_U = [0.01011, 0.01120, 0.01240, 0.01340, 0.01380, 0.01350, 0.01250, 0.01100,
           0.00960, 0.00860, 0.00800, 0.00770, 0.00750, 0.00660, 0.00580, 0.00500,
           0.00440, 0.00390, 0.00342, 0.00320, 0.00280, 0.00220, 0.00160, 0.00100]
CROOK_Z = [0.0000, 0.0022, 0.0050, 0.0080, 0.0102, 0.0118, 0.0127, 0.0128,
           0.0118, 0.0100, 0.0076, 0.0054, 0.0039, 0.00385, 0.00365, 0.00315,
           0.00235, 0.00135, 0.00022, -0.00130, -0.00260, -0.00340, -0.00375, -0.00370]
INK = '#2c231a'
ACCENT = '#b06a1e'
STEEL = '#6a6f77'
BOWL_FILL = '#f2cf5f'
HANDLE_FILL = '#efe7da'


def wire_path(kind, radius, n=240):
    if kind == 'eye':
        a0, a1 = math.radians(262.0), math.radians(98.0)
    else:
        a0, a1 = math.radians(-82.0), math.radians(82.0)
    u = np.linspace(0, 1, n)
    ang = a0 + (a1 - a0) * u
    f = np.clip(np.exp(-((u / 0.075) ** 2)) + np.exp(-(((1 - u) / 0.075) ** 2)), 0, 1)
    r = radius + (R_J - radius) * f
    return r * np.cos(ang), r * np.sin(ang)


def handle_outline(side):
    xs = [side * s[0] for s in HANDLE_STATIONS]
    ws = [s[1] / 2 for s in HANDLE_STATIONS]
    return [(x, w) for x, w in zip(xs, ws)] + \
           [(x, -w) for x, w in zip(reversed(xs), reversed(ws))]


def fig_plan():
    fig, ax = plt.subplots(figsize=(10.2, 7.4), dpi=200)
    ax.set_aspect('equal')
    ax.axis('off')

    th = np.linspace(0, 2 * np.pi, 720)
    rr = 0.0846 * (1 + 0.030 * np.cos(12 * th))
    ax.fill(rr * np.cos(th), rr * np.sin(th), color=BOWL_FILL, alpha=0.45,
            ec='#b08a25', lw=1.4, zorder=1)
    ax.plot(0.0609 * np.cos(th), 0.0609 * np.sin(th), '--', color='#8a6a2a',
            lw=1.0, alpha=0.7, zorder=2)

    for rad in (R_IN, R_OUT):
        x, y = wire_path('eye', rad)
        ax.plot(x, y, color=STEEL, lw=2.2, solid_capstyle='round', zorder=5)
        x, y = wire_path('hook', rad)
        ax.plot(x, y, color=STEEL, lw=2.2, solid_capstyle='round', zorder=5)
    for ey in (-R_J, R_J):
        ax.add_patch(Annulus((0.0, ey), EYE_MAJOR, 2 * EYE_LOOP_R,
                             color=ACCENT, alpha=0.95, zorder=7))
    for ey in (-R_J, R_J):
        sgn = 1 if ey > 0 else -1
        for s in (-1, 1):
            xx = s * np.array([0.0105, 0.0120, 0.0118, 0.0090, 0.0072])
            yy = ey + sgn * np.array([0.0020, 0.0010, 0.0030, 0.0042, 0.0040])
            ax.plot(xx, yy, color='#c8952f', lw=2.0, solid_capstyle='round', zorder=8)
    for side in (-1, 1):
        ax.add_patch(Polygon(handle_outline(side), closed=True, fc=HANDLE_FILL,
                             ec='#9c8f7b', lw=1.2, zorder=6))
        ax.add_patch(plt.Rectangle((side * 0.0810 - (0.004 if side > 0 else 0), -0.0050),
                                   0.004, 0.0100, fc=STEEL, ec='none', zorder=7))

    # labels
    ax.annotate('碗（碗口 φ173 / 碗腰 φ121）', xy=(-0.048, 0.058), xytext=(-0.128, 0.118),
                fontsize=12.5, color=INK, ha='center',
                arrowprops=dict(arrowstyle='-', color=INK, lw=0.9))
    ax.annotate('孔 · 眼环\n（A 夹两端改弯）', xy=(0.002, R_J + 0.005), xytext=(0.045, 0.118),
                fontsize=12.5, color=ACCENT, ha='left', fontweight='bold',
                arrowprops=dict(arrowstyle='->', color=ACCENT, lw=1.3))
    ax.annotate('钩 · 弯钩\n（B 夹两端改弯）', xy=(0.002, -R_J - 0.005), xytext=(0.048, -0.130),
                fontsize=12.5, color=ACCENT, ha='left', fontweight='bold',
                arrowprops=dict(arrowstyle='->', color=ACCENT, lw=1.3))
    ax.annotate('双钢丝 U 型环＋鱼形手柄（均不变）', xy=(-0.052, 0.030), xytext=(-0.190, 0.062),
                fontsize=12.0, color=INK, ha='center',
                arrowprops=dict(arrowstyle='-', color=INK, lw=0.9))
    # approach arrows + names
    ax.annotate('', xy=(-0.212, -0.062), xytext=(-0.275, -0.062),
                arrowprops=dict(arrowstyle='-|>', color='#4a6f9c', lw=2.2))
    ax.annotate('', xy=(0.212, -0.062), xytext=(0.275, -0.062),
                arrowprops=dict(arrowstyle='-|>', color='#4a6f9c', lw=2.2))
    ax.text(-0.245, -0.098, 'A 夹（孔夹）', fontsize=13.5, color='#3c5a80', ha='center')
    ax.text(0.245, -0.098, 'B 夹（钩夹）', fontsize=13.5, color='#3c5a80', ha='center')
    ax.text(0.0, 0.140, '两夹从左右合围 → 端头在碗前/后相接', fontsize=13, color='#3c5a80',
            ha='center')
    ax.plot([-0.242, -0.192], [-0.152, -0.152], color=INK, lw=3)
    ax.text(-0.217, -0.162, '50 mm', fontsize=10.5, color=INK, ha='center')
    ax.set_xlim(-0.30, 0.30)
    ax.set_ylim(-0.175, 0.155)
    fig.tight_layout(pad=0.1)
    path = os.path.join(OUT, 'diagram_plan.png')
    fig.savefig(path, transparent=True)
    plt.close(fig)
    print('wrote', path)


def fig_lock():
    fig = plt.figure(figsize=(8.4, 7.2), dpi=200)

    # ---------------- top: wedge self-lock cross-section
    ax = fig.add_axes([0.03, 0.50, 0.94, 0.46])
    ax.set_aspect('equal')
    ax.axis('off')
    zc = CONTACT_Z
    outer = np.array(BOWL_OUTER)
    ax.fill(np.r_[outer[:, 0], -outer[::-1, 0]],
            np.r_[outer[:, 1], outer[::-1, 1]], color=BOWL_FILL, alpha=0.5,
            ec='#a8842a', lw=1.6, zorder=1)
    inner = np.array(BOWL_INNER)
    ax.plot(np.r_[inner[:, 0], -inner[::-1, 0]],
            np.r_[inner[:, 1], inner[::-1, 1]], color='#a8842a', lw=1.1, zorder=2)
    for s in (-1, 1):
        for rad in (R_IN, R_OUT):
            ax.add_patch(Circle((s * rad, zc), 0.0040, fc='#5d626b', ec='#33363b',
                                lw=0.6, zorder=5))
        xs = [s * st[0] for st in HANDLE_STATIONS]
        hs = [st[1] * 0.5 for st in HANDLE_STATIONS]
        top = [(x, zc + 0.0060 + h) for x, h in zip(xs, hs)]
        bot = [(x, zc + 0.0060 - h) for x, h in zip(reversed(xs), reversed(hs))]
        ax.add_patch(Polygon(top + bot, closed=True, fc=HANDLE_FILL, ec='#9c8f7b',
                             lw=1.0, zorder=4))
        ax.annotate('', xy=(s * 0.150, zc + 0.008 + 0.024), xytext=(s * 0.150, zc + 0.008),
                    arrowprops=dict(arrowstyle='-|>', color='#22558c', lw=2.6))
        ax.text(s * 0.150, zc + 0.040, 'F', fontsize=15, color='#22558c',
                ha='center', fontweight='bold')
        ax.text(s * 0.150 - s * 0.030, zc + 0.052, '手提力', fontsize=11, color='#22558c',
                ha='center')
        d = np.array([s * 0.62, 0.78])
        p0 = np.array([s * (R_IN - 0.002), zc])
        ax.annotate('', xy=p0 + d * 0.036, xytext=p0,
                    arrowprops=dict(arrowstyle='-|>', color='#276b3d', lw=2.2))
    ax.annotate('', xy=(0, 0.030), xytext=(0, 0.088),
                arrowprops=dict(arrowstyle='-|>', color='#8c2f22', lw=3.0))
    ax.text(0.010, 0.080, 'G', fontsize=16, color='#8c2f22', fontweight='bold')
    ax.text(0.028, 0.078, '碗＋食物重力', fontsize=11.5, color='#8c2f22')
    ax.text(0.082, zc + 0.030, 'N', fontsize=13, color='#276b3d', fontweight='bold')
    ax.text(0.0, -0.014, '钢环卡在最宽处（碗口）下方：刚性闭合环无法越过 → 楔紧自锁',
            fontsize=11.5, color=INK, ha='center')
    ax.text(0.0, 0.130, '① 楔紧自锁（剖面示意）', fontsize=14.5, color=ACCENT,
            ha='center', fontweight='bold')
    ax.set_xlim(-0.25, 0.25)
    ax.set_ylim(-0.030, 0.145)

    # ---------------- bottom: joint inset
    ax2 = fig.add_axes([0.08, 0.02, 0.84, 0.44])
    ax2.set_aspect('equal')
    ax2.axis('off')
    ax2.add_patch(Annulus((0.0, 0.0), EYE_MAJOR, 2 * EYE_LOOP_R, color='#8a8f97',
                          ec='#3c3f45', lw=1.0, zorder=3))
    ax2.plot(CROOK_U, CROOK_Z, color='#c8952f', lw=3.6, solid_capstyle='round', zorder=4)
    ax2.annotate('', xy=(-0.030, 0.000), xytext=(-0.011, 0.000),
                 arrowprops=dict(arrowstyle='-|>', color='#8c2f22', lw=2.6))
    ax2.annotate('', xy=(0.030, 0.0035), xytext=(0.011, 0.0035),
                 arrowprops=dict(arrowstyle='-|>', color='#8c2f22', lw=2.6))
    ax2.text(-0.036, 0.0040, 'T', fontsize=16, color='#8c2f22', fontweight='bold')
    ax2.text(0.030, 0.0090, 'T', fontsize=16, color='#8c2f22', fontweight='bold')
    ax2.annotate('孔（眼环）', xy=(-0.0045, -0.0065), xytext=(-0.040, -0.0205),
                 fontsize=12, color='#4d535b', fontweight='bold',
                 arrowprops=dict(arrowstyle='->', color='#4d535b', lw=1.1))
    ax2.annotate('钩（弯钩）', xy=(0.0128, 0.0105), xytext=(0.020, 0.0205),
                 fontsize=12, color='#a8752a', fontweight='bold',
                 arrowprops=dict(arrowstyle='->', color='#a8752a', lw=1.1))
    ax2.text(0.0, -0.0285, '碗重产生的环向拉力 T 使钩尖压向孔壁、钩颈搭在孔环上表面\n→ 越重越紧，端头不会脱开',
             fontsize=11.5, color=INK, ha='center')
    ax2.text(0.0, 0.0250, '② 端头互锁：孔 ＋ 钩', fontsize=14.5, color=ACCENT,
             ha='center', fontweight='bold')
    ax2.set_xlim(-0.045, 0.045)
    ax2.set_ylim(-0.036, 0.031)

    path = os.path.join(OUT, 'diagram_lock.png')
    fig.savefig(path, transparent=True)
    plt.close(fig)
    print('wrote', path)


if __name__ == '__main__':
    fig_plan()
    fig_lock()
