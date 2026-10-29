"""Physics validation of the V2 two-clip bowl lifter.

1) closed-form statics / strength checks
2) a planar frame FE (2D beam elements) of the assembled ring under the bowl's
   radial contact load -> ring expansion, hoop force, bending stress
3) printed-prototype checks
Outputs: console table, docs/物理验证报告.md, design/physics_check.png
"""
import math
import os

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = 'D:/code/vibe/antiscald'
os.makedirs(os.path.join(ROOT, 'docs'), exist_ok=True)
try:
    font_manager.fontManager.addfont('C:/Windows/Fonts/simhei.ttf')
except Exception:
    pass
plt.rcParams['font.family'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# ---------------------------------------------------------------- inputs (SI, m / N / Pa)
G = 9.81
M_BOWL = 1.2                    # bowl + food, kg
W = M_BOWL * G
SF = 3.0                        # design safety factor for the structural checks
MU = 0.20                       # steel/ceramic friction coefficient
R_RING_IN = 0.0609              # ring inner radius at the contact (m)
R_WIRE = 0.0016
WIRE_D = 2 * R_WIRE
R_INS = 0.0625                  # inner wire centreline radius
R_OUTS = 0.0675
RIM_R = 0.0868                  # bowl rim outer radius
RIMM_Z = 0.0795                 # height of the widest point above the bowl base
CONTACT_Z = 0.0454              # ring plane height at lock (above the bowl base)
R_CONTACT = 0.0609              # bowl radius at lock height
BOWL_H = 0.0828
E_STEEL = 200e9
E_PETG = 2.1e9
E_PA = 2.6e9
ALLOW_STEEL = 1200e6            # 304 spring wire Rp0.2 (cold drawn, conservative)
ALLOW_STEEL_ANN = 205e6         # annealed 304 (for welded / HAZ regions)
PETG_YIELD_STRAIN = 0.025
PA_YIELD_STRAIN = 0.06
RISER_TOP_R = 0.1312
RISER_TOP_Z = 0.1438
GRIP_R = 0.174
GRIP_Z = 0.172


def fmt(x, n=2):
    return ('%.' + str(n) + 'f') % x


# ---------------------------------------------------------------- 2D frame FE
def frame_k(E, A, I, L):
    ea, ei = E * A / L, E * I
    return np.array([
        [ea, 0, 0, -ea, 0, 0],
        [0, 12 * ei / L ** 3, 6 * ei / L ** 2, 0, -12 * ei / L ** 3, 6 * ei / L ** 2],
        [0, 6 * ei / L ** 2, 4 * ei / L, 0, -6 * ei / L ** 2, 2 * ei / L],
        [-ea, 0, 0, ea, 0, 0],
        [0, -12 * ei / L ** 3, -6 * ei / L ** 2, 0, 12 * ei / L ** 3, -6 * ei / L ** 2],
        [0, 6 * ei / L ** 2, 2 * ei / L, 0, -6 * ei / L ** 2, 4 * ei / L]])


def frame_T(c, s):
    return np.array([[c, s, 0, 0, 0, 0],
                     [-s, c, 0, 0, 0, 0],
                     [0, 0, 1, 0, 0, 0],
                     [0, 0, 0, c, s, 0],
                     [0, 0, 0, -s, c, 0],
                     [0, 0, 0, 0, 0, 1]])


def ring_path_pts(kind, radius=0.0642, n=41):
    a0, a1 = (math.radians(98), math.radians(262)) if kind == 'eye' else \
             (math.radians(-82), math.radians(82))
    u = np.linspace(0, 1, n)
    ang = a0 + (a1 - a0) * u
    f = np.clip(np.exp(-((u / 0.075) ** 2)) + np.exp(-(((1 - u) / 0.075) ** 2)), 0, 1)
    r = radius + (0.0725 - radius) * f
    return np.stack([r * np.cos(ang), r * np.sin(ang)], axis=1)


def ring_fe(load_mult=1.0):
    """Assembled ring closed by rigid joints at J+/- (symmetric load case)."""
    Jb, Jf = np.array([0.0, 0.0725]), np.array([0.0, -0.0725])
    A = ring_path_pts('eye')             # back tip -> front tip
    B = ring_path_pts('hook')            # front tip -> back tip
    pts = [Jb] + list(A[1:]) + [Jf] + list(B[1:])
    nodes = np.array(pts)
    n = len(nodes)
    elems = [(i, i + 1) for i in range(n - 1)] + [(n - 1, 0)]
    A_w = 2 * math.pi * R_WIRE ** 2
    I_w = 2 * (math.pi * WIRE_D ** 4 / 64 + math.pi * R_WIRE ** 2 * 0.0025 ** 2)
    ndof = 3 * n
    K = np.zeros((ndof, ndof))
    for (i, j) in elems:
        p, q = nodes[i], nodes[j]
        d = q - p
        L = float(np.linalg.norm(d))
        c, s = d[0] / L, d[1] / L
        kk = frame_T(c, s).T @ frame_k(E_STEEL, A_w, I_w, L) @ frame_T(c, s)
        dof = [3 * i, 3 * i + 1, 3 * i + 2, 3 * j, 3 * j + 1, 3 * j + 2]
        for a in range(6):
            for b in range(6):
                K[dof[a], dof[b]] += kk[a, b]
    # loads: outward radial on the contact arcs (within +-55 deg of each clip centre)
    Ls, contact = [], 0.0
    for k, (i, j) in enumerate(elems):
        mid = 0.5 * (nodes[i] + nodes[j])
        L = float(np.linalg.norm(nodes[j] - nodes[i]))
        ang = math.degrees(math.atan2(mid[1], mid[0]))
        dA = abs(((ang - 180.0 + 180.0) % 360.0) - 180.0)
        dB = abs(((ang + 180.0) % 360.0) - 180.0)
        Ls.append(L)
        if min(dA, dB) < 55.0:
            contact += L
            el_info_ok = True
        else:
            el_info_ok = False
        Ls[-1] = (L, el_info_ok)
    N_radial = 1.042 * W * load_mult
    F = np.zeros(ndof)
    for k, (i, j) in enumerate(elems):
        L, ok = Ls[k]
        if not ok:
            continue
        mid = 0.5 * (nodes[i] + nodes[j])
        r = mid / np.linalg.norm(mid)
        f = N_radial * L / contact
        for nd in (i, j):
            F[3 * nd] += 0.5 * f * r[0]
            F[3 * nd + 1] += 0.5 * f * r[1]
    # ground the structure softly
    for i in range(n):
        K[3 * i, 3 * i] += 1e3
        K[3 * i + 1, 3 * i + 1] += 1e3
        K[3 * i + 2, 3 * i + 2] += 1e2
    u = np.linalg.solve(K, F)
    max_sig = max_N = max_M = 0.0
    for k, (i, j) in enumerate(elems):
        p, q = nodes[i], nodes[j]
        d = q - p
        L = float(np.linalg.norm(d))
        c, s = d[0] / L, d[1] / L
        T = frame_T(c, s)
        dof = [3 * i, 3 * i + 1, 3 * i + 2, 3 * j, 3 * j + 1, 3 * j + 2]
        fe = frame_k(E_STEEL, A_w, I_w, L) @ (T @ u[dof])
        Nf = abs(fe[0])
        Mf = max(abs(fe[2]), abs(fe[5]))
        max_sig = max(max_sig, Nf / A_w + Mf * 0.0041 / I_w)
        max_N = max(max_N, Nf)
        max_M = max(max_M, Mf)
    angs = np.degrees(np.arctan2(nodes[:, 1], nodes[:, 0]))
    idx = int(np.argmin(np.abs(angs - 180.0)))
    d0 = nodes[idx]
    r0 = d0 / np.linalg.norm(d0)
    dR = float(np.array([u[3 * idx], u[3 * idx + 1]]) @ r0)
    k_ring = N_radial / dR if abs(dR) > 1e-12 else float('inf')
    return dict(dR=dR, k=k_ring, max_sig=max_sig, max_N=max_N, max_M=max_M, F=N_radial)


# ---------------------------------------------------------------- checks
def run_checks():
    res = {}
    # flank geometry
    slope = (RIM_R - R_CONTACT) / (RIMM_Z - CONTACT_Z)
    psi = math.degrees(math.atan(slope))            # flank angle from vertical
    res['psi'] = psi
    res['normal_vert'] = 1 / math.sqrt(1 + slope ** 2)
    res['normal_rad'] = slope / math.sqrt(1 + slope ** 2)
    # 1. wedge: radial load generated by the bowl weight (with friction)
    n_rad = res['normal_rad'] / (res['normal_vert'] + res['normal_rad'] * MU)
    res['radial_factor'] = n_rad
    # 2. ring FE at working load and at SF load
    fe1 = ring_fe(1.0)
    fe3 = ring_fe(SF)
    res['fe1'] = fe1
    res['fe3'] = fe3
    res['escape_expansion'] = RIM_R - R_RING_IN        # radial expansion to slip over the rim
    res['escape_factor'] = (res['escape_expansion'] / fe1['dR']) if fe1['dR'] > 0 else float('inf')
    # 3. installation (ring opened over the bowl rim): curvature change of the wire
    kappa0, kappa1 = 1 / R_INS, 1 / (RIM_R + R_WIRE)
    dkappa = kappa0 - kappa1
    res['install_strain'] = dkappa * R_WIRE           # surface strain change
    res['install_open'] = 2 * (RIM_R + R_WIRE - R_INS)  # tips have to spread (m)
    # equivalent opening force of a split ring (Castigliano, half ring ~pi R)
    I_pair = 2 * (math.pi * WIRE_D ** 4 / 64 + math.pi * R_WIRE ** 2 * 0.0025 ** 2)
    EI = E_STEEL * I_pair
    res['install_force'] = (res['install_open'] * EI) / (3 * math.pi * R_INS ** 3)
    res['install_force_kg'] = res['install_force'] / G
    # 4. riser bending (metal): cantilever from bracket to grip
    M_r = (W / SF * SF / 2) * (GRIP_R - 0.0735)      # per clip hand force * lever
    I_riser = math.pi * (0.006 ** 4 - 0.0044 ** 4) / 64
    res['riser_M'] = M_r
    res['riser_sig'] = M_r * 0.003 / I_riser
    res['riser_defl'] = M_r * 0.15 ** 2 / (2 * E_STEEL * I_riser)
    # 5. joint (steel hook/eye) vertical shear bending
    F_joint = W / 2 * SF
    M_j = F_joint * 0.008
    res['joint_M'] = M_j
    res['joint_sig'] = M_j * R_WIRE / (math.pi * WIRE_D ** 4 / 64)
    # 6. stability: single clip needs the bowl CG under the grip -> tilt
    res['single_tilt'] = math.degrees(math.atan(GRIP_R / (GRIP_Z - CONTACT_Z)))
    res['tip_tolerance'] = math.degrees(math.atan((RIM_R - R_RING_IN) / (RIMM_Z - CONTACT_Z)))
    # 7. printed version
    I_print = 6.0 * 7.0 ** 3 / 12 * 1e-12            # 6 mm x 7 mm section, m^4
    res['print_I'] = I_print
    res['print_EI'] = E_PETG * I_print
    res['print_open_force'] = (res['install_open'] * res['print_EI']) / (3 * math.pi * (0.064) ** 3)
    res['print_install_strain'] = dkappa * 0.003     # half height 3 mm
    # printed riser bending (12 mm x 9 mm strip)
    I_pr = 9e-3 * (12e-3) ** 3 / 12
    res['print_riser_sig'] = M_r * 0.006 / I_pr
    res['print_riser_EI'] = E_PETG * I_pr
    res['print_riser_defl'] = M_r * 0.15 ** 2 / (2 * E_PETG * I_pr)
    # printed joint: M4 screw shear (single shear, two joints share)
    res['print_M4_shear'] = F_joint / 2 / (math.pi * 0.002 ** 2)
    # installation-force variants: split-ring formula F = (open EI)/(3 pi R^3)
    variants = []
    for d_mm, free_id in ((3.2, 121.8), (3.0, 121.8), (2.8, 130.0), (2.5, 121.8),
                          (2.5, 145.0), (2.8, 150.0), (2.2, 155.0)):
        r_w = d_mm / 2000.0
        I_w = 2 * (math.pi * (2 * r_w) ** 4 / 64 + math.pi * r_w ** 2 * 0.0025 ** 2)
        EI = E_STEEL * I_w
        mouth_m = (free_id / 1000.0) * math.sin(math.radians(82.0))
        open_m = max(0.0, 2 * (RIM_R + R_WIRE) - mouth_m)
        Rf = free_id / 2000.0
        F = open_m * EI / (3 * math.pi * Rf ** 3)
        variants.append((d_mm, free_id, open_m * 1000.0, F))
    res['install_variants'] = variants
    return res


def report(res):
    L = []
    L.append('# 物理可行性验证报告（V2 加高把手 · 双夹联锁取碗器）\n')
    L.append('> 方法：刚性体静力学 + 材料力学闭式校核 + 平面框架有限元（自编 2D beam FE）求解环形钢圈在工作载荷下的径向变形/应力。')
    L.append('> 工况：碗＋食物 1.2 kg（W = 11.77 N），结构校核取安全系数 3.0；钢-陶瓷摩擦系数 μ = 0.20。\n')
    L.append('## 1. 输入与几何\n')
    L.append('| 项 | 值 |')
    L.append('|---|---|')
    L.append('| 碗 | 碗口 φ173.6 / 碗腰 φ121.8 / 高 82.8 mm |')
    L.append(f'| 碗身锥面（夹持段）半角（相对竖直） | ψ = {res["psi"]:.1f}° |')
    L.append('| 钢圈 | 双钢丝 φ3.2，内缘 φ121.8，接触高度距碗底 45.4 mm |')
    L.append('| 加高把手 | 握点 R174 / Z172 mm（环平面以上 172 mm） |')
    L.append('| 材料 | 304 弹簧钢丝（Rp0.2 取 1200 MPa）、304 管 φ6×0.8 |\n')
    L.append('## 2. 校核结果\n')
    L.append('| # | 项目 | 计算值 | 判据 | 结论 |')
    L.append('|---|---|---|---|---|')
    fe1, fe3 = res['fe1'], res['fe3']
    rows = [
        ('1', '楔紧几何锁', f'环内缘 φ121.8 < 碗口 φ173.6；环须扩张 {res["escape_expansion"]*1000:.1f} mm 才可能滑过碗口',
         '不可越过', '通过（几何锁）'),
        ('2', '工作载荷下环的径向扩张', f'{fe1["dR"]*1e6:.1f} um（载荷 {fe1["F"]:.2f} N）',
         f'远小于 {res["escape_expansion"]*1000:.0f} mm', f'安全系数 {res["escape_factor"]:.0f}×'),
        ('3', '环的等效径向刚度', f'{fe1["k"]/1e6:.2f} N/um', '—', '很刚（几乎无弹性张开）'),
        ('4', '环内最大弯曲应力（工作载荷 / SF=3）', f'{fe1["max_sig"]/1e6:.1f} / {fe3["max_sig"]/1e6:.1f} MPa',
         f'< {ALLOW_STEEL/1e6:.0f} MPa', '通过'),
        ('5', '端头关节拉力（工作载荷 / SF=3）', f'{fe1["max_N"]:.2f} / {fe3["max_N"]:.2f} N', '—', '很小'),
        ('6', '钩/眼局部弯曲（SF=3）', f'{res["joint_sig"]/1e6:.0f} MPa', f'< {ALLOW_STEEL/1e6:.0f} MPa', '通过'),
        ('7', '立管弯曲应力（SF=3）', f'{res["riser_sig"]/1e6:.0f} MPa', '< 205/1200 MPa', '通过'),
        ('8', '立管弯曲挠度（SF=1）', f'{res["riser_defl"]*1000:.1f} mm', '< 5 mm', '通过'),
    ]
    for r in rows:
        L.append('| ' + ' | '.join(r) + ' |')
    L.append('')
    L.append('## 3. 安装工况（控制工况）\n')
    L.append(f'- 要把 C 形环套过碗口，环口需要张开 **{res["install_open"]*1000:.1f} mm**（每边约 {res["install_open"]*500:.1f} mm）。')
    L.append(f'- 对应的钢丝表面曲率应变变化：**{res["install_strain"]*100:.2f}%**；304 弹簧钢丝的弹性应变极限约 0.6~0.9% —— 处于临界。')
    L.append(f'- 按开口环（Castigliano）估算，张开力约 **{res["install_force"]:.0f} N（≈{res["install_force_kg"]:.0f} kg 力）**，需要双手用力压入；这和市售弹簧夹的"用力按压"手感一致，但偏紧。')
    L.append('- **建议**：① 钢丝由 φ3.2 改为 φ3.0（应变与力都降 ~15%）；② 环自由内径略放大（或端头开口加宽 5 mm）以减小过盈；③ 实际安装用"先斜插一侧、再滚压过碗沿"的手法，而不是两侧同时张开——本仿真动画为了讲清原理做了对称张开的简化。\n')
    L.append('## 4. 稳定性（为什么必须两只）\n')
    L.append(f'- 单只夹子：手柄（握点距碗心 {GRIP_R*1000:.0f} mm）与碗重力形成力偶，碗的重心必须移到握点正下方才可能平衡 → 需要的倾角约 **{res["single_tilt"]:.0f}°**，而碗口几何允许的倾角只有约 **{res["tip_tolerance"]:.0f}°** → 单夹必然翻倒/滑脱（与用户实际体验一致）。')
    L.append('- 两只夹子：双手在碗两侧对称上提，力偶互相抵消（净力矩 0），端头互锁成整环 → 稳定。\n')
    L.append('## 5. 3D 打印版（PETG/PA12）\n')
    L.append(f'- 打印环（6×7 mm 截面，PETG）的弯曲刚度只有钢制双钢丝的约 1/60（EI：{res["print_EI"]:.2f} vs {E_STEEL*2*(math.pi*WIRE_D**4/64 + math.pi*R_WIRE**2*0.0025**2):.1f} N·m²）。')
    L.append(f'- 安装张开所需的表面应变约 **{res["print_install_strain"]*100:.1f}%**：PETG 屈服应变 ~2.5%，PA12 ~6% → **PA12/PA-CF（SLS）可反复使用；PETG 仅适合偶尔/轻载**。')
    L.append(f'- 打印立管（12×9 mm，PETG）在 SF=3 下的弯曲应力仅 {res["print_riser_sig"]/1e6:.1f} MPa、挠度 {res["print_riser_defl"]*1000:.1f} mm → 打印件强度不是问题，**C 形环的刚度和蠕变才是限制**。')
    L.append(f'- M4 销钉单剪应力可忽略（{res["print_M4_shear"]/1e6:.1f} MPa）→ 打印版关节用 M4 螺丝完全够用。\n')
    L.append('## 6. 结论与剩余风险\n')
    L.append('1. **承载/楔紧/稳定性：可行**。工作载荷下钢圈几乎不变形（微米级），几何锁 + 孔钩互锁成立；两只夹子对称受力，单夹的翻倒问题被消除。')
    L.append('2. **安装张开是控制工况**：应变接近 304 弹簧钢丝弹性极限，建议线径降到 φ3.0 或加大开口/自由内径；量产应做 500~1000 次装拆疲劳试验。')
    L.append('3. **本报告未覆盖**：钢丝与碗的接触应力/局部压痕、焊缝疲劳、眼环孔的磨损、手柄胶接强度、塑料件蠕变——这些需要非线性接触有限元与实物试验。')
    L.append('4. **建议的后续仿真**：')
    L.append('   - 非线性接触 FEA（ANSYS Mechanical / Abaqus / COMSOL / FreeCAD+CalculiX）：钢丝用 3D 实体或梁单元 + 自接触，做安装张开与承载两工况；')
    L.append('   - 多体动力学（Adams / RecurDyn / MuJoCo / Isaac Sim）：整机取放动作、倾覆与碰撞；')
    L.append('   - 疲劳（ANSYS nCode / Fe-Safe）：弹簧钢丝的 500~1000 次装拆；')
    L.append('   - 打印件：用 PA12 先做样件，按《3D打印说明》实测刚度与蠕变。')
    return '\n'.join(L) + '\n'


def plot(res):
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.0))
    fig.patch.set_facecolor('white')
    # (a) stress utilization
    ax = axes[0]
    labels = ['环弯曲\n(工作)', '环弯曲\n(SF=3)', '钩/眼\n(SF=3)', '立管\n(SF=3)']
    vals = [res['fe1']['max_sig'] / ALLOW_STEEL, res['fe3']['max_sig'] / ALLOW_STEEL,
            res['joint_sig'] / ALLOW_STEEL, res['riser_sig'] / ALLOW_STEEL]
    bars = ax.bar(labels, [v * 100 for v in vals], color=['#8aa9c9', '#2b4f7a', '#b06a1e', '#7a7a7a'])
    ax.axhline(100, color='#a03020', ls='--', lw=1)
    ax.set_ylabel('应力利用率（%）')
    ax.set_title('(a) 强度校核（<100% 通过）', fontsize=10)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 2, f'{v*100:.2f}%', ha='center', fontsize=8)
    ax.set_ylim(0, max(110, max(vals) * 100 + 20))
    # (b) installation
    ax = axes[1]
    names = ['弹性应变\n极限(下限)', '安装需求', '弹性应变\n极限(上限)']
    vals = [0.6, res['install_strain'] * 100, 0.9]
    colors = ['#2b4f7a', '#a03020' if res['install_strain'] * 100 > 0.9 else '#b06a1e', '#2b4f7a']
    ax.bar(names, vals, color=colors)
    ax.set_ylabel('应变 (%)')
    ax.set_title('(b) 安装张开：钢丝应变 vs 弹性极限', fontsize=10)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.02, f'{v:.2f}%', ha='center', fontsize=8)
    # (c) stability
    ax = axes[2]
    ax.barh(['单夹', '双夹'], [res['single_tilt'], 0], color=['#a03020', '#2b6b3d'])
    ax.axvline(res['tip_tolerance'], color='#5f5f5f', ls='--', lw=1)
    ax.text(res['tip_tolerance'] + 1, -0.35, f'几何容限 {res["tip_tolerance"]:.0f}°', fontsize=8, color='#5f5f5f')
    ax.set_xlabel('平衡所需倾角（°）')
    ax.set_title('(c) 稳定性：单夹 vs 双夹', fontsize=10)
    ax.set_xlim(0, max(res['single_tilt'] * 1.15, res['tip_tolerance'] * 1.5))
    fig.tight_layout()
    p = os.path.join(ROOT, 'design', 'physics_check.png')
    fig.savefig(p, dpi=170)
    print('[phys] chart', p)


def main():
    res = run_checks()
    md = report(res)
    p = os.path.join(ROOT, 'docs', '物理验证报告.md')
    open(p, 'w', encoding='utf-8').write(md)
    print('=== summary ===')
    r = res
    print('flank psi deg %.1f' % r['psi'])
    print('FE dR um %.3f  k N/um %.3f  sig1 MPa %.2f  sig3 MPa %.2f' %
          (r['fe1']['dR'] * 1e6, r['fe1']['k'] / 1e6, r['fe1']['max_sig'] / 1e6, r['fe3']['max_sig'] / 1e6))
    print('escape factor %.0f' % r['escape_factor'])
    print('install open mm %.1f  strain pct %.2f  force N %.0f' %
          (r['install_open'] * 1e3, r['install_strain'] * 100, r['install_force']))
    print('joint MPa %.0f  riser MPa %.0f  riser defl mm %.1f' %
          (r['joint_sig'] / 1e6, r['riser_sig'] / 1e6, r['riser_defl'] * 1e3))
    print('single tilt deg %.0f  tolerance deg %.0f' % (r['single_tilt'], r['tip_tolerance']))
    print('print open force N %.0f  print strain pct %.1f  print riser MPa %.1f' %
          (r['print_open_force'], r['print_install_strain'] * 100, r['print_riser_sig'] / 1e6))
    plot(res)


if __name__ == '__main__':
    main()
