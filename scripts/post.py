"""Post-production: grade rendered frames, add captions/labels/end card, encode MP4."""
import argparse
import glob
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = 'D:/code/vibe/antiscald'
FRAMES_IN = os.path.join(ROOT, 'video', 'frames')
FRAMES_OUT = os.path.join(ROOT, 'video', 'post')
VIDEO_OUT = os.path.join(ROOT, 'video', 'two_clip_bowl_lifter_demo.mp4')
W, H = 1280, 720
FPS = 24
FONT_REG = 'C:/Windows/Fonts/msyh.ttc'
FONT_BOLD = 'C:/Windows/Fonts/msyhbd.ttc'

BADGE = '双夹联锁取碗器 · 方案仿真'

TITLE = '双夹联锁 · 双防烫夹取碗方案'
SUBTITLE = '两夹左右合围　·　孔钩互锁　·　碗重自锁'
TITLE_NOTE = '原理动画 · 省略人手 · U 型钢圈结构不变'

STEPS = [
    (44, 124, '①  双夹左右合围', '夹环从两侧进入，高度在碗腰，不经过碗底'),
    (128, 174, '②  钩夹下放，钩尖落入孔中', '钩在孔的上方，垂直落座'),
    (178, 272, '③  端头互锁，环抱碗身', '碗重把钢环撑紧，钩被孔壁压住 → 自锁'),
    (276, 418, '④  提起、移动、放置', '两侧手柄对称受力，不再侧翻'),
    (422, 465, '⑤  落桌松环，上提钩夹卸锁', '孔钩反向脱开，两夹退出'),
]

END_TITLE = '结构不变 · 只在两端做文章'
END_LINES = [
    'U 型双钢丝圈 / 鱼形手柄 / 金属支架 —— 保持原样',
    '一个夹的两端 → 弯成「孔」（眼环）',
    '另一个夹的两端 → 弯成「钩」（弯钩）',
    '双夹互锁成整环：碗越重，环抱越紧，端头越锁死',
]
END_NOTE = '不改变 U 型结构 · 不增加任何附加铁丝'


# ------------------------------------------------------------------ helpers
def font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def text_size(draw, txt, fnt):
    box = draw.textbbox((0, 0), txt, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def draw_pill(draw, xy, txt, fnt, fg=(255, 255, 255, 235), bg=(20, 15, 10, 150),
              pad=(18, 10), accent=None):
    x, y = xy
    tw, th = text_size(draw, txt, fnt)
    w = tw + pad[0] * 2
    h = th + pad[1] * 2 + 4
    layer = Image.new('RGBA', (w + 8, h + 8), (0, 0, 0, 0))
    d2 = ImageDraw.Draw(layer)
    d2.rounded_rectangle([4, 4, w + 3, h + 3], radius=h // 2, fill=bg)
    if accent:
        d2.rounded_rectangle([4, 4, 12, h + 3], radius=4, fill=accent)
    d2.text((pad[0] + (8 if accent else 0) + 4, pad[1] + 2), txt, font=fnt, fill=fg)
    return layer, (x, y, x + w + 8, y + h + 8)


def grade(arr):
    """arr float32 HxWx3 0..1 -> graded."""
    x = arr.copy()
    # gentle contrast + slight lift
    x = (x - 0.46) * 1.07 + 0.46
    # saturation
    lum = (0.299 * x[..., 0] + 0.587 * x[..., 1] + 0.114 * x[..., 2])[..., None]
    x = lum + (x - lum) * 1.07
    # warm tint
    x[..., 0] *= 1.025
    x[..., 2] *= 0.975
    # vignette
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = W * 0.5, H * 0.48
    r = np.sqrt(((xx - cx) / (W * 0.62)) ** 2 + ((yy - cy) / (H * 0.62)) ** 2)
    vig = np.clip(1.0 - 0.26 * np.clip(r - 0.35, 0, 3) ** 1.5, 0.55, 1.0)
    x *= vig[..., None]
    # subtle grain
    rng = np.random.default_rng(1234)
    x += rng.normal(0, 0.006, x.shape).astype(np.float32)
    return np.clip(x, 0, 1)


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def ramp(f, a, b):
    return smooth((f - a) / max(b - a, 1))


def overlay_alpha(img, f, f0, f1, fade=8):
    """Return alpha multiplier for an overlay visible f0..f1 with fades."""
    if f < f0 or f > f1:
        return 0.0
    a = min(ramp(f, f0, f0 + fade), 1.0)
    b = 1.0 - ramp(f, f1 - fade, f1)
    return min(a, b)


def add_badge(img, alpha):
    if alpha <= 0:
        return img
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    fnt = font(20)
    tw, th = text_size(d, BADGE, fnt)
    x, y = 40, 30
    d.rounded_rectangle([x - 12, y - 8, x + tw + 12, y + th + 12], radius=6,
                        fill=(15, 12, 9, int(110 * alpha)))
    d.rectangle([x - 12, y - 8, x - 9, y + th + 12], fill=(214, 152, 62, int(220 * alpha)))
    d.text((x, y), BADGE, font=fnt, fill=(255, 248, 238, int(225 * alpha)))
    return Image.alpha_composite(img.convert('RGBA'), layer)


def add_title(img, alpha):
    if alpha <= 0:
        return img
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    # soft dark band behind title
    band = Image.new('RGBA', img.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    bd.rectangle([0, int(H * 0.52), W, int(H * 0.86)], fill=(12, 9, 6, int(90 * alpha)))
    band = band.filter(ImageFilter.GaussianBlur(28))
    layer = Image.alpha_composite(layer, band)
    d = ImageDraw.Draw(layer)
    f1, f2, f3 = font(58, True), font(31), font(21)
    tw1, th1 = text_size(d, TITLE, f1)
    tw2, th2 = text_size(d, SUBTITLE, f2)
    tw3, _ = text_size(d, TITLE_NOTE, f3)
    d.text(((W - tw1) / 2 + 2, H * 0.575 + 2), TITLE, font=f1, fill=(0, 0, 0, int(140 * alpha)))
    d.text(((W - tw1) / 2, H * 0.575), TITLE, font=f1, fill=(255, 249, 240, int(250 * alpha)))
    d.text(((W - tw2) / 2, H * 0.575 + th1 + 26), SUBTITLE, font=f2,
           fill=(232, 196, 140, int(235 * alpha)))
    d.text(((W - tw3) / 2, H * 0.575 + th1 + th2 + 66), TITLE_NOTE, font=f3,
           fill=(210, 200, 188, int(180 * alpha)))
    d.line([(W / 2 - 80, H * 0.575 + th1 + 12), (W / 2 + 80, H * 0.575 + th1 + 12)],
           fill=(214, 152, 62, int(200 * alpha)), width=2)
    return Image.alpha_composite(img.convert('RGBA'), layer)


def add_steps(img, f):
    for (f0, f1, title, sub) in STEPS:
        a = overlay_alpha(img, f, f0, f1, fade=10)
        if a <= 0:
            continue
        layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        ft, fs = font(30, True), font(21)
        tw_t, th_t = text_size(d, title, ft)
        tw_s, th_s = text_size(d, sub, fs)
        w = max(tw_t, tw_s) + 56
        h = th_t + th_s + 34
        x, y = 46, H - h - 46
        box = Image.new('RGBA', (w + 10, h + 10), (0, 0, 0, 0))
        bd = ImageDraw.Draw(box)
        bd.rounded_rectangle([5, 5, w + 4, h + 4], radius=14, fill=(16, 12, 8, int(140 * a)))
        bd.rectangle([5, 5, 12, h + 4], fill=(214, 152, 62, int(230 * a)))
        bd.text((28, 16), title, font=ft, fill=(255, 250, 243, int(250 * a)))
        bd.text((28, 20 + th_t), sub, font=fs, fill=(226, 210, 190, int(215 * a)))
        full = Image.new('RGBA', layer.size, (0, 0, 0, 0))
        full.alpha_composite(box, (x, y))
        layer = Image.alpha_composite(layer, full)
        img = Image.alpha_composite(img.convert('RGBA'), layer)
        return img
    return img


def add_joint_labels(img, f):
    """Annotate eye (孔) and hook (钩) during the close-up."""
    a = overlay_alpha(img, f, 129, 173, fade=8)
    if a <= 0:
        return img
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    fnt = font(21, True)
    # anchor points measured on the close-up framing
    eye = (505, 527)
    hook = (658, 250)

    def callout(target, text, text_pos, side=1):
        tx, ty = text_pos
        tw, th = text_size(d, text, fnt)
        d.line([target, (tx + (0 if side > 0 else tw), ty + th // 2)],
               fill=(240, 224, 200, int(190 * a)), width=2)
        d.ellipse([target[0] - 5, target[1] - 5, target[0] + 5, target[1] + 5],
                  outline=(240, 224, 200, int(230 * a)), width=2)
        d.rounded_rectangle([tx - 10, ty - 5, tx + tw + 10, ty + th + 9], radius=6,
                            fill=(16, 12, 8, int(150 * a)))
        d.text((tx, ty), text, font=fnt, fill=(255, 246, 232, int(240 * a)))

    callout(eye, '孔 · 眼环（A 夹端头）', (196, 424), side=1)
    callout(hook, '钩 · 弯钩（B 夹端头）', (800, 300), side=1)
    return Image.alpha_composite(img.convert('RGBA'), layer)


def add_end_card(img, f):
    a = overlay_alpha(img, f, 466, 516, fade=12)
    if a <= 0:
        return img
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rectangle([0, 0, W, H], fill=(12, 9, 6, int(150 * a)))
    f1, f2, f3 = font(46, True), font(27), font(20)
    tw1, th1 = text_size(d, END_TITLE, f1)
    d.text(((W - tw1) / 2, H * 0.20), END_TITLE, font=f1, fill=(255, 249, 240, int(250 * a)))
    d.line([(W / 2 - 90, H * 0.20 + th1 + 18), (W / 2 + 90, H * 0.20 + th1 + 18)],
           fill=(214, 152, 62, int(210 * a)), width=2)
    y = H * 0.20 + th1 + 48
    for i, line in enumerate(END_LINES):
        tw, th = text_size(d, line, f2)
        d.text(((W - tw) / 2, y), line, font=f2,
               fill=(238, 230, 218, int(235 * a)) if i else (255, 244, 228, int(245 * a)))
        y += th + 22
    twn, thn = text_size(d, END_NOTE, f3)
    d.text(((W - twn) / 2, y + 18), END_NOTE, font=f3, fill=(206, 178, 136, int(210 * a)))
    return Image.alpha_composite(img.convert('RGBA'), layer)


def process_frame(path, out_path, f):
    im = Image.open(path).convert('RGB')
    arr = np.asarray(im).astype(np.float32) / 255.0
    arr = grade(arr)
    img = Image.fromarray((arr * 255.0 + 0.5).astype(np.uint8), 'RGB').convert('RGBA')

    # global fades
    fade = 1.0
    if f <= 10:
        fade = min(fade, ramp(f, 0, 10))
    if f >= 506:
        fade = min(fade, 1.0 - ramp(f, 506, 516))
    if fade < 1.0:
        black = Image.new('RGBA', img.size, (8, 6, 5, 255))
        img = Image.blend(black, img, fade)

    img = add_badge(img, overlay_alpha(img, f, 16, 468, fade=14))
    img = add_title(img, overlay_alpha(img, f, 2, 48, fade=12))
    img = add_joint_labels(img, f)
    img = add_steps(img, f)
    img = add_end_card(img, f)
    img.convert('RGB').save(out_path, 'PNG', compress_level=3)
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='f0', type=int, default=1)
    ap.add_argument('--to', dest='f1', type=int, default=516)
    ap.add_argument('--encode', action='store_true')
    ap.add_argument('--preview', type=str, default='')  # comma frame list
    args = ap.parse_args()
    os.makedirs(FRAMES_OUT, exist_ok=True)

    if args.preview:
        os.makedirs(os.path.join(ROOT, 'tests', 'preview'), exist_ok=True)
        for fr in [int(x) for x in args.preview.split(',')]:
            src = os.path.join(FRAMES_IN, f'f_{fr:04d}.png')
            if not os.path.exists(src):
                print('missing', src)
                continue
            dst = os.path.join(ROOT, 'tests', 'preview', f'p_{fr:04d}.png')
            process_frame(src, dst, fr)
            print('preview', dst)
        return

    n = 0
    for f in range(args.f0, args.f1 + 1):
        src = os.path.join(FRAMES_IN, f'f_{f:04d}.png')
        if not os.path.exists(src):
            print('missing frame', f)
            continue
        process_frame(src, os.path.join(FRAMES_OUT, f'f_{f:04d}.png'), f)
        n += 1
        if n % 50 == 0:
            print('post', f)
    print('post done', n)

    if args.encode:
        import imageio_ffmpeg
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [ff, '-y', '-framerate', str(FPS),
               '-i', os.path.join(FRAMES_OUT, 'f_%04d.png'),
               '-c:v', 'libx264', '-preset', 'slow', '-crf', '17',
               '-pix_fmt', 'yuv420p', '-movflags', '+faststart', VIDEO_OUT]
        print(' '.join(cmd))
        subprocess.run(cmd, check=True)
        print('video:', VIDEO_OUT)


if __name__ == '__main__':
    main()
