"""Annotate the 3D joint macro still with labels (dark pills + leader lines)."""
from PIL import Image, ImageDraw, ImageFont

SRC = 'D:/code/vibe/antiscald/design/joint_macro.png'
DST = 'D:/code/vibe/antiscald/design/joint_macro_labeled.png'
FONT = 'C:/Windows/Fonts/msyh.ttc'
FONTB = 'C:/Windows/Fonts/msyhbd.ttc'

img = Image.open(SRC).convert('RGBA')
W, H = img.size
layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(layer)
fb = ImageFont.truetype(FONTB, 34)
fs = ImageFont.truetype(FONT, 24)


def pill(pos, title, sub, anchor='left'):
    x, y = pos
    tw = max(d.textlength(title, font=fb), d.textlength(sub, font=fs)) + 44
    th = 92
    if anchor == 'right':
        x -= tw
    d.rounded_rectangle([x, y, x + tw, y + th], radius=18, fill=(18, 13, 8, 190))
    d.rectangle([x, y + 14, x + 7, y + th - 14], fill=(214, 152, 62, 235))
    d.text((x + 22, y + 12), title, font=fb, fill=(255, 248, 236, 245))
    d.text((x + 22, y + 52), sub, font=fs, fill=(224, 205, 180, 225))
    return (x, y, x + tw, y + th)


# leader + pill for eye (孔)
eye_anchor = (760, 640)
eye_pill = (-1, -1)
# choose pill bottom-left
ex, ey = 60, H - 210
box = pill((ex, ey), '孔 · 眼环（A 夹端头）', '双钢丝端头并拢弯成 360° 眼环，末端焊合')
d.line([eye_anchor, (ex + 300, ey + 46)], fill=(240, 226, 205, 210), width=3)
d.ellipse([eye_anchor[0] - 8, eye_anchor[1] - 8, eye_anchor[0] + 8, eye_anchor[1] + 8],
          outline=(245, 232, 210, 240), width=3)

# leader + pill for hook (钩)
hook_anchor = (1020, 300)
hx, hy = W - 830, 70
box2 = pill((hx, hy), '钩 · 弯钩（B 夹端头）', '端头并拢起弯成钩，钩尖向下、开口朝内')
d.line([hook_anchor, (hx + 40, hy + 50)], fill=(240, 226, 205, 210), width=3)
d.ellipse([hook_anchor[0] - 8, hook_anchor[1] - 8, hook_anchor[0] + 8, hook_anchor[1] + 8],
          outline=(245, 232, 210, 240), width=3)

out = Image.alpha_composite(img, layer)
out.convert('RGB').save(DST, 'PNG')
print('wrote', DST, out.size)
