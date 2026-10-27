"""Compose the design sheet (PNG) from diagrams + 3D stills."""
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = 'D:/code/vibe/antiscald'
OUT = os.path.join(ROOT, 'design')
W, H = 2000, 1680
CREAM = (244, 239, 230)
PANEL = (251, 247, 240)
INK = (44, 35, 26)
SOFT = (108, 94, 78)
ACCENT = (176, 106, 30)
FONT = 'C:/Windows/Fonts/msyh.ttc'
FONTB = 'C:/Windows/Fonts/msyhbd.ttc'


def font(sz, bold=False):
    return ImageFont.truetype(FONTB if bold else FONT, sz)


def text(d, xy, s, f, fill=INK, anchor='la'):
    d.text(xy, s, font=f, fill=fill, anchor=anchor)


def panel(img, box, r=24):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(box, radius=r, fill=PANEL, outline=(222, 211, 192), width=2)


def paste_fit(canvas, path, box, pad=14, autocrop=True):
    im = Image.open(path).convert('RGBA')
    if autocrop:
        bbox = im.split()[-1].getbbox()
        if bbox:
            m = 24
            bbox = (max(0, bbox[0] - m), max(0, bbox[1] - m),
                    min(im.width, bbox[2] + m), min(im.height, bbox[3] + m))
            im = im.crop(bbox)
    bw = box[2] - box[0] - 2 * pad
    bh = box[3] - box[1] - 2 * pad
    sc = min(bw / im.width, bh / im.height)
    nw, nh = max(1, int(im.width * sc)), max(1, int(im.height * sc))
    im = im.resize((nw, nh), Image.LANCZOS)
    x = box[0] + (box[2] - box[0] - nw) // 2
    y = box[1] + (box[3] - box[1] - nh) // 2
    canvas.alpha_composite(im, (x, y))
    return (x, y, x + nw, y + nh)


def main():
    img = Image.new('RGBA', (W, H), CREAM + (255,))
    d = ImageDraw.Draw(img)
    d.rectangle([18, 18, W - 19, H - 19], outline=(206, 192, 170), width=3)

    # ---------------- header
    text(d, (66, 52), '防烫夹改造方案  /  DESIGN  PROPOSAL', font(21, True), ACCENT)
    text(d, (64, 84), '双夹联锁取碗器', font(64, True), INK)
    text(d, (68, 182), '两个防烫夹  ·  左右合围  ·  孔钩互锁  ·  碗重自锁', font(29), SOFT)
    text(d, (W - 70, 96), 'U 型钢圈结构不变', font(27, True), ACCENT, anchor='ra')
    text(d, (W - 70, 138), '不增加任何附加铁丝结构', font(23), SOFT, anchor='ra')
    text(d, (W - 70, 180), '仅改两端端头：孔 / 钩', font(23), SOFT, anchor='ra')
    d.line([(66, 222), (W - 66, 222)], fill=(206, 192, 170), width=2)

    # ---------------- panel 1 : plan diagram
    p1 = (60, 244, 1090, 910)
    panel(img, p1)
    text(d, (p1[0] + 26, p1[1] + 20), '①  结构改动（俯视示意）', font(30, True), INK)
    text(d, (p1[0] + 26, p1[1] + 62), '原 U 型双钢丝环与鱼形手柄全部保留，仅把四个自由端弯成「孔」或「钩」',
         font(19), SOFT)
    paste_fit(img, os.path.join(OUT, 'diagram_plan.png'),
              (p1[0] + 8, p1[1] + 92, p1[2] - 8, p1[3] - 10))

    # ---------------- panel 2 : 3d joint macro
    p2 = (1110, 244, 1940, 910)
    panel(img, p2)
    text(d, (p2[0] + 26, p2[1] + 20), '②  关节细节（3D 渲染）', font(30, True), INK)
    text(d, (p2[0] + 26, p2[1] + 62), '钩从上方落入孔中；碗重把环撑紧后，钩尖压向孔壁、钩颈搭在孔环上表面',
         font(19), SOFT)
    macro = os.path.join(OUT, 'joint_macro_labeled.png')
    if not os.path.exists(macro):
        macro = os.path.join(OUT, 'joint_macro.png')
    paste_fit(img, macro, (p2[0] + 12, p2[1] + 96, p2[2] - 12, p2[3] - 56))
    text(d, (p2[0] + 26, p2[3] - 40),
         '眼环外径 19 mm / 孔 φ10 mm　·　钩高 15 mm / 钩丝 φ3.2 mm　·　装配余隙 ≤ 1 mm',
         font(18), SOFT)

    # ---------------- panel 3 : lock principle
    p3 = (60, 930, 1120, 1616)
    panel(img, p3)
    text(d, (p3[0] + 26, p3[1] + 20), '③  为什么更稳：楔紧自锁 + 端头互锁', font(30, True), INK)
    paste_fit(img, os.path.join(OUT, 'diagram_lock.png'),
              (p3[0] + 8, p3[1] + 76, p3[2] - 8, p3[3] - 10))

    # ---------------- panel 4 : lists
    p4 = (1140, 930, 1940, 1616)
    panel(img, p4)
    x0, y = p4[0] + 30, p4[1] + 24
    text(d, (x0, y), '改动清单', font(28, True), ACCENT)
    y += 52
    groups = [
        ('保持不变', ['U 型双钢丝圈（Ø138 mm，弹簧夹持不变）', '鱼形手柄 + 金属 V 形支架 / 卡箍',
                   '夹持方式、材料、热处理工艺']),
        ('只有两处改动', ['A 夹两端 → 并拢弯成「孔」眼环（360° 闭环）',
                    'B 夹两端 → 并拢弯成「钩」弯钩（开口朝内）',
                    '两夹端头互锁，两个半环合成一个整环']),
        ('稳定性来源', ['两侧手柄对称提拉 → 无附加翻转扭矩',
                   '楔紧 + 环向拉力 → 碗越重，环抱越紧',
                   '四点端头互锁 → 抗晃动、抗脱开']),
    ]
    for title, lines in groups:
        text(d, (x0, y), '· ' + title, font(23, True), INK)
        y += 36
        for ln in lines:
            text(d, (x0 + 26, y), '—  ' + ln, font(19), SOFT)
            y += 30
        y += 14
    # usage steps
    y += 6
    d.line([(x0, y), (p4[2] - 30, y)], fill=(222, 211, 192), width=2)
    y += 16
    text(d, (x0, y), '使用步骤', font(23, True), ACCENT)
    y += 38
    steps = ['① 两夹从左右在碗腰合围（不经过碗底）',
             '② 钩夹下放，钩尖落入孔夹的两个眼环',
             '③ 双手同时上提，钢环楔紧 → 碗被锁住提起',
             '④ 落桌后松环，上提钩夹，两夹向两侧退出']
    for s in steps:
        text(d, (x0 + 4, y), s, font(19), INK)
        y += 32

    # ---------------- footer
    d.line([(66, H - 62), (W - 66, H - 62)], fill=(206, 192, 170), width=2)
    text(d, (66, H - 50),
         '适用条件：碗口明显大于碗腰（最宽处在夹持高度之上）。碗越重、碗口越大，楔紧越可靠。',
         font(18), SOFT)
    text(d, (W - 66, H - 50), '仿真视频：two_clip_bowl_lifter_demo.mp4  ·  24 fps',
         font(18), SOFT, anchor='ra')

    out = os.path.join(OUT, 'design_sheet.png')
    img.convert('RGB').save(out, 'PNG')
    print('wrote', out, img.size)


if __name__ == '__main__':
    main()
