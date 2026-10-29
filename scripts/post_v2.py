"""Post-production for the V2 pot video (reuses the V1 post module helpers)."""
import argparse
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import post

ROOT = 'D:/code/vibe/antiscald'
post.FRAMES_IN = os.path.join(ROOT, 'video', 'frames_v2')
post.FRAMES_OUT = os.path.join(ROOT, 'video', 'post_v2')
VIDEO_OUT = os.path.join(ROOT, 'video', 'two_clip_pot_v2_demo.mp4')
W, H = 1280, 720
F_END = 500

post.BADGE = '双夹联锁取碗器 V2 · 锅中取碗'
post.TITLE = 'V2 加高把手 · 从锅里取碗'
post.SUBTITLE = '双夹从锅口放入　·　孔钩互锁　·　上提取出'
post.TITLE_NOTE = '原理动画 · 省略人手 · 钢环张开为钢丝弹性变形'
post.STEPS = [
    (30, 118, '①  孔夹从锅口放入', '两臂张开跨过碗沿，落在碗腰'),
    (120, 198, '②  钩夹从对侧放入', '同样套过碗沿，停在孔夹上方'),
    (202, 238, '③  钩尖落入孔中，端头互锁', '两夹连成整环，环抱碗身'),
    (242, 372, '④  上提把手，钢环楔紧', '碗被锁住，提过锅沿、移出'),
    (376, 458, '⑤  放碗、卸钩、两夹退出', '钢环卸载后，钩尖可抽出'),
]
post.END_TITLE = 'V2 加高把手 · 锅中取碗'
post.END_LINES = ['U 型钢环 / 孔钩端头 —— 结构不变',
                  'V 形支架以上加立管：手柄抬到环平面上方 144 mm',
                  '手在锅沿以上操作，锅壁不再挡手',
                  '孔钩互锁成整环：碗越重，环抱越紧']
post.END_NOTE = '只改把手高度 · 孔钩与自锁原理不变'


def add_joint_labels(img, f):
    return img


def add_end_card(img, f):
    a = post.overlay_alpha(img, f, 456, F_END, fade=12)
    if a <= 0:
        return img
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rectangle([0, 0, W, H], fill=(12, 9, 6, int(150 * a)))
    f1, f2, f3 = post.font(46, True), post.font(27), post.font(20)
    tw1, th1 = post.text_size(d, post.END_TITLE, f1)
    d.text(((W - tw1) / 2, H * 0.18), post.END_TITLE, font=f1, fill=(255, 249, 240, int(250 * a)))
    d.line([(W / 2 - 90, H * 0.18 + th1 + 18), (W / 2 + 90, H * 0.18 + th1 + 18)],
           fill=(214, 152, 62, int(210 * a)), width=2)
    y = H * 0.18 + th1 + 48
    for i, line in enumerate(post.END_LINES):
        tw, th = post.text_size(d, line, f2)
        d.text(((W - tw) / 2, y), line, font=f2,
               fill=(238, 230, 218, int(235 * a)) if i else (255, 244, 228, int(245 * a)))
        y += th + 22
    twn, thn = post.text_size(d, post.END_NOTE, f3)
    d.text(((W - twn) / 2, y + 18), post.END_NOTE, font=f3, fill=(206, 178, 136, int(210 * a)))
    return Image.alpha_composite(img.convert('RGBA'), layer)


def process_frame(path, out_path, f):
    im = Image.open(path).convert('RGB')
    arr = np.asarray(im).astype(np.float32) / 255.0
    arr = post.grade(arr)
    img = Image.fromarray((arr * 255.0 + 0.5).astype(np.uint8), 'RGB').convert('RGBA')
    fade = 1.0
    if f <= 10:
        fade = min(fade, post.ramp(f, 0, 10))
    if f >= F_END - 10:
        fade = min(fade, 1.0 - post.ramp(f, F_END - 10, F_END))
    if fade < 1.0:
        black = Image.new('RGBA', img.size, (8, 6, 5, 255))
        img = Image.blend(black, img, fade)
    img = post.add_badge(img, post.overlay_alpha(img, f, 14, 452, fade=14))
    img = post.add_title(img, post.overlay_alpha(img, f, 2, 46, fade=12))
    img = post.add_steps(img, f)
    img = add_end_card(img, f)
    img.convert('RGB').save(out_path, 'PNG', compress_level=3)
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='f0', type=int, default=1)
    ap.add_argument('--to', dest='f1', type=int, default=F_END)
    ap.add_argument('--encode', action='store_true')
    args = ap.parse_args()
    os.makedirs(post.FRAMES_OUT, exist_ok=True)
    n = 0
    for f in range(args.f0, args.f1 + 1):
        src = os.path.join(post.FRAMES_IN, 'f_%04d.png' % f)
        if not os.path.exists(src):
            print('missing', src)
            continue
        process_frame(src, os.path.join(post.FRAMES_OUT, 'f_%04d.png' % f), f)
        n += 1
        if n % 50 == 0:
            print('[v2post]', f, flush=True)
    print('[v2post] done', n)
    if args.encode:
        import imageio_ffmpeg
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [ff, '-y', '-framerate', '24', '-i', os.path.join(post.FRAMES_OUT, 'f_%04d.png'),
               '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p',
               '-movflags', '+faststart', VIDEO_OUT]
        subprocess.run(cmd, check=True)
        print('[v2post] video', VIDEO_OUT, round(os.path.getsize(VIDEO_OUT) / 1e6, 2), 'MB')


if __name__ == '__main__':
    main()
