"""Design system of the GTK window: palette, CSS, line icons and the custom drawn widgets
(format ring, picture viewer with area selection and comparison, sound wave). Same look as
the Android app."""
from __future__ import annotations
import math,re,subprocess,threading,time
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,Gdk,GdkPixbuf,GLib
import cairo
gi.require_version('PangoCairo','1.0')

ACCENTS=[('#6e5fd8','#9a8df2'),('#2f74d9','#6ca4f5'),('#1e9466','#4cc394'),('#d9573f','#f08a73'),('#c54383','#e57cb0')]

def rgb(hexa):hexa=hexa.lstrip('#');return tuple(int(hexa[i:i+2],16)/255 for i in (0,2,4))
def hexa(c):return '#%02x%02x%02x'%tuple(int(max(0,min(1,v))*255+.5) for v in c)
def blend(a,b,t):a,b=rgb(a),rgb(b);return hexa(tuple(a[i]*(1-t)+b[i]*t for i in range(3)))

def palette(dark,accent=0):
    a=ACCENTS[max(0,min(len(ACCENTS)-1,accent))][1 if dark else 0]
    if dark:p=dict(bg='#131218',surface='#1c1b22',surface2='#24222c',border='#33303d',text='#eceaf3',muted='#a19eaf',segment='#2a2833',danger='#e5646e',success='#4cc394',on_accent='#17142a')
    else:p=dict(bg='#f6f5f2',surface='#ffffff',surface2='#efedf5',border='#e4e1eb',text='#1e1d24',muted='#6b6878',segment='#f1f0ec',danger='#c23c47',success='#1e9466',on_accent='#ffffff')
    p['accent']=a;p['accent_soft']=blend(a,p['surface'] if dark else '#ffffff',0.78 if dark else 0.86)
    p['accent_text']=blend(a,'#ffffff',0.35) if dark else blend(a,'#000000',0.18)
    p['danger_soft']=blend(p['danger'],p['surface'],0.75 if dark else 0.88);p['success_soft']=blend(p['success'],p['surface'],0.8)
    p['drop_border']=blend(a,p['surface2'],0.55);p['dark']=dark
    return p

CSS='''
window, .background { background-color: @bg; color: @text; }
* { outline-color: alpha(@accent,0.5); }
.sidebar { background-color: @surface; border-right: 1px solid @border; padding: 14px 12px; }
.brand { font-size: 17px; font-weight: 700; color: @text; }
.brand-sub { font-size: 12px; color: @muted; }
button.nav { background-image: none; background-color: transparent; border: none; box-shadow: none; border-radius: 12px; padding: 9px 12px; color: @text; }
button.nav label { color: @text; font-size: 14px; }
button.nav:hover { background-color: @surface2; }
button.nav.on { background-color: @accent_soft; }
button.nav.on label { color: @accent_text; font-weight: 700; }
.title { font-size: 28px; font-weight: 800; color: @text; }
.section { font-size: 16px; font-weight: 700; color: @text; }
.head { font-size: 18px; font-weight: 700; color: @text; }
.muted { color: @muted; }
.small { color: @muted; font-size: 12px; }
.caption { color: @muted; font-size: 13px; font-weight: 700; }
.mono { font-family: monospace; font-size: 12px; color: @text; background-color: @surface2; border-radius: 12px; padding: 10px 12px; }
.card { background-color: @surface; border: 1px solid @border; border-radius: 18px; padding: 16px; }
.drop { background-color: @surface2; border: 2px dashed @drop_border; border-radius: 22px; padding: 26px; }
.drop.hover { border-color: @accent; border-style: solid; background-color: @accent_soft; }
.row-card { background-color: @surface; border: 1px solid @border; border-radius: 16px; padding: 8px 10px; }
.row-card:hover { border-color: @drop_border; }
button { background-image: none; box-shadow: none; text-shadow: none; -gtk-icon-shadow: none; }
button.pill { border-radius: 24px; padding: 10px 18px; font-weight: 700; border: 1px solid transparent; }
button.primary { background-color: @accent; color: @on_accent; }
button.primary label { color: @on_accent; }
button.primary:hover { background-color: shade(@accent,1.07); }
button.soft { background-color: @accent_soft; color: @accent_text; }
button.soft label { color: @accent_text; }
button.soft:hover { background-color: shade(@accent_soft,0.97); }
button.plain { background-color: transparent; border-color: @border; color: @text; }
button.plain label { color: @text; }
button.plain:hover { background-color: @surface2; }
button.danger { background-color: @danger_soft; color: @danger; }
button.danger label { color: @danger; }
button:disabled { opacity: 0.45; }
button.icon { background-color: transparent; border: none; border-radius: 20px; padding: 6px; min-width: 0; min-height: 0; }
button.icon:hover { background-color: @surface2; }
button.chip { background-color: @surface; border: 1px solid @border; border-radius: 19px; padding: 6px 14px; }
button.chip label { color: @text; }
button.chip:hover { background-color: @surface2; }
button.chip.on { background-color: @accent_soft; border-color: @accent; }
button.chip.on label { color: @accent_text; font-weight: 700; }
.seg { background-color: @surface2; border: 1px solid @border; border-radius: 24px; padding: 4px; }
button.seg-item { background-color: transparent; border: none; border-radius: 20px; padding: 8px 12px; }
button.seg-item label { color: @text; font-weight: 700; }
button.seg-item.on { background-color: @accent; }
button.seg-item.on label { color: @on_accent; }
button.tile { background-color: @surface; border: 1px solid @border; border-radius: 16px; padding: 12px 6px 10px 6px; }
button.tile:hover { background-color: @surface2; }
button.tile.on { background-color: @accent_soft; border-color: @accent; }
button.tile label { color: @text; font-size: 13px; }
button.tile.on label { color: @accent_text; font-weight: 700; }
button.tile label.new-tag, .new-tag { background-color: @success; color: #ffffff; border-radius: 8px; padding: 0 6px; font-size: 9px; font-weight: 800; }
.badge-box { border-radius: 12px; }
entry { background-image: none; background-color: @surface2; color: @text; border: 1px solid @border; border-radius: 12px; padding: 8px 12px; box-shadow: none; }
entry:focus { border-color: @accent; }
checkbutton label { color: @text; }
check { background-image: none; background-color: @surface; border: 1px solid @border; border-radius: 5px; min-width: 16px; min-height: 16px; }
check:checked { background-color: @accent; border-color: @accent; color: @on_accent; -gtk-icon-source: -gtk-icontheme("object-select-symbolic"); }
progressbar trough { min-height: 8px; border-radius: 8px; background-color: @surface2; border: none; }
progressbar progress { min-height: 8px; border-radius: 8px; background-image: none; background-color: @accent; border: none; }
scrolledwindow, viewport { background-color: transparent; border: none; }
scrollbar { background-color: transparent; border: none; }
scrollbar slider { background-color: @border; border-radius: 999px; min-width: 7px; min-height: 7px; }
textview, textview text { background-color: @surface2; color: @text; }
tooltip, tooltip.background { background-color: @surface2; color: @text; border-radius: 8px; }
tooltip label { color: @text; }
scale trough { background-color: @surface2; border: none; border-radius: 6px; min-height: 6px; }
scale highlight { background-color: @accent; border: none; border-radius: 6px; }
scale slider { background-image: none; background-color: @surface; border: 2px solid @accent; border-radius: 50%; min-width: 16px; min-height: 16px; box-shadow: none; }
.swatch { border-radius: 20px; min-width: 34px; min-height: 34px; padding: 0; border: 3px solid transparent; }
.swatch.on { border-color: @text; }
'''

def css(p):
    defines=''.join(f'@define-color {k} {v};\n' for k,v in p.items() if isinstance(v,str))
    sw=''.join(f'button.swatch-{i} {{ background-color: {ACCENTS[i][1 if p["dark"] else 0]}; }}\n' for i in range(len(ACCENTS)))
    return (defines+CSS+sw).encode()

# ---------------------------------------------------------------- icons (Material, Apache 2.0)
ICONS={
 'home':'M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z',
 'history':'M13 3c-4.97 0-9 4.03-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42C8.27 19.99 10.51 21 13 21c4.97 0 9-4.03 9-9s-4.03-9-9-9zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z',
 'tune':'M3 17v2h6v-2H3zM3 5v2h10V5H3zm10 16v-2h8v-2h-8v-2h-2v6h2zM7 9v2H3v2h4v2h2V9H7zm14 4v-2H11v2h10zm-6-4h2V7h4V5h-4V3h-2v6z',
 'upload':'M9 16h6v-6h4l-7-7-7 7h4zm-4 2h14v2H5z',
 'folder':'M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z',
 'play':'M8 5v14l11-7z','stop':'M6 6h12v12H6z',
 'close':'M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z',
 'back':'M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z',
 'check':'M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z',
 'cut':'M9.64 7.64c.23-.5.36-1.05.36-1.64 0-2.21-1.79-4-4-4S2 3.79 2 6s1.79 4 4 4c.59 0 1.14-.13 1.64-.36L10 12l-2.36 2.36C7.14 14.13 6.59 14 6 14c-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4c0-.59-.13-1.14-.36-1.64L12 14l7 7h3v-1L9.64 7.64zM6 8c-1.1 0-2-.89-2-2s.9-2 2-2 2 .89 2 2-.9 2-2 2zm0 12c-1.1 0-2-.89-2-2s.9-2 2-2 2 .89 2 2-.9 2-2 2zm6-7.5c-.28 0-.5-.22-.5-.5s.22-.5.5-.5.5.22.5.5-.22.5-.5.5zM19 3l-6 6 2 2 7-7V3z',
 'video':'M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4h-4z',
 'audio':'M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z',
 'image':'M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z',
 'doc':'M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z',
 'wand':'M7.5 5.6L10 7 8.6 4.5 10 2 7.5 3.4 5 2l1.4 2.5L5 7zm12 9.8L17 14l1.4 2.5L17 19l2.5-1.4L22 19l-1.4-2.5L22 14zM22 2l-2.5 1.4L17 2l1.4 2.5L17 7l2.5-1.4L22 7l-1.4-2.5zm-7.63 5.29c-.39-.39-1.02-.39-1.41 0L1.29 18.96c-.39.39-.39 1.02 0 1.41l2.34 2.34c.39.39 1.02.39 1.41 0L16.7 11.05c.39-.39.39-1.02 0-1.41l-2.33-2.35zm-1.03 5.49l-2.12-2.12 2.44-2.44 2.12 2.12-2.44 2.44z',
 'wave':'M7 18h2V6H7v12zm4 4h2V2h-2v20zm-8-8h2v-4H3v4zm12 4h2V6h-2v12zm4-8v4h2v-4h-2z',
 'rotate':'M15.55 5.55L11 1v3.07C7.06 4.56 4 7.92 4 12s3.05 7.44 7 7.93v-2.02c-2.84-.48-5-2.94-5-5.91s2.16-5.43 5-5.91V10l4.55-4.45zM19.93 11c-.17-1.39-.72-2.73-1.62-3.89l-1.42 1.42c.54.75.88 1.6 1.02 2.47h2.02zM13 17.9v2.02c1.39-.17 2.74-.71 3.9-1.61l-1.44-1.44c-.75.54-1.59.89-2.46 1.03zm3.89-2.42l1.42 1.41c.9-1.16 1.45-2.5 1.62-3.89h-2.02c-.14.87-.48 1.72-1.02 2.48z',
 'speed':'M4 18l8.5-6L4 6v12zm9-12v12l8.5-6L13 6z',
 'mute':'M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z',
 'volume':'M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z',
 'camera':'M12 15.2a3.2 3.2 0 1 0 0-6.4 3.2 3.2 0 0 0 0 6.4zM9 2L7.17 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2h-3.17L15 2H9zm3 15c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5z',
 'subtitles':'M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zM4 12h4v2H4v-2zm10 6H4v-2h10v2zm6 0h-4v-2h4v2zm0-4H10v-2h10v2z',
 'mic':'M12 14c1.66 0 2.99-1.34 2.99-3L15 5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.3-3c0 3-2.54 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.41 2.72 6.23 6 6.72V21h2v-3.28c3.28-.48 6-3.3 6-6.72h-1.7z',
 'merge':'M17 20.41L18.41 19 15 15.59 13.59 17 17 20.41zM7.5 8H11v5.59L5.59 19 7 20.41l6-6V8h3.5L12 3.5 7.5 8z',
 'split':'M14 4l2.29 2.29-2.88 2.88 1.42 1.42 2.88-2.88L20 10V4zm-4 0H4v6l2.29-2.29 4.71 4.7V20h2v-8.41l-5.29-5.3z',
 'delete':'M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z',
 'text':'M2.5 4v3h5v12h3V7h5V4h-13zm19 5h-9v3h3v7h3v-7h3V9z',
 'gif':'M11.5 9H13v6h-1.5zM9 9H6c-.6 0-1 .5-1 1v4c0 .5.4 1 1 1h3c.6 0 1-.5 1-1v-2H8.5v1.5h-2v-3H10V10c0-.5-.4-1-1-1zm10 1.5V9h-4.5v6H16v-2h2v-1.5h-2v-1z',
 'add':'M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z',
 'open':'M19 19H5V5h7V3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2v-7h-2v7zM14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3h-7z',
 'compress':'M8 19h3v3h2v-3h3l-4-4-4 4zm8-15h-3V1h-2v3H8l4 4 4-4zM4 9v2h16V9H4zm0 3h16v2H4z',
 'info':'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z',
 'pages':'M11.99 18.54l-7.37-5.73L3 14.07l9 7 9-7-1.63-1.27-7.38 5.74zM12 16l7.36-5.73L21 9l-9-7-9 7 1.63 1.27L12 16z',
 'eye':'M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z',
 'chevron':'M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z','chevron_left':'M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z',
 'palette':'M12 3c-4.97 0-9 4.03-9 9s4.03 9 9 9c.83 0 1.5-.67 1.5-1.5 0-.39-.15-.74-.39-1.01-.23-.26-.38-.61-.38-.99 0-.83.67-1.5 1.5-1.5H16c2.76 0 5-2.24 5-5 0-4.42-4.03-8-9-8zm-5.5 9c-.83 0-1.5-.67-1.5-1.5S5.67 9 6.5 9 8 9.67 8 10.5 7.33 12 6.5 12zm3-4C8.67 8 8 7.33 8 6.5S8.67 5 9.5 5s1.5.67 1.5 1.5S10.33 8 9.5 8zm5 0c-.83 0-1.5-.67-1.5-1.5S13.67 5 14.5 5s1.5.67 1.5 1.5S15.33 8 14.5 8zm3 4c-.83 0-1.5-.67-1.5-1.5S16.67 9 17.5 9s1.5.67 1.5 1.5-.67 1.5-1.5 1.5z',
 'translate':'M12.87 15.07l-2.54-2.51.03-.03c1.74-1.94 2.98-4.17 3.71-6.53H17V4h-7V2H8v2H1v1.99h11.17C11.5 7.92 10.44 9.75 9 11.35 8.07 10.32 7.3 9.19 6.69 8h-2c.73 1.63 1.73 3.17 2.98 4.56l-5.09 5.02L4 19l5-5 3.11 3.11.76-2.04zM18.5 10h-2L12 22h2l1.12-3h4.75L21 22h2l-4.5-12zm-2.62 7l1.62-4.33L19.12 17h-3.24z',
 'lock':'M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z',
 'build':'M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.7C.4 7.1.9 10.1 2.9 12.1c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.4z',
}
_TOKEN=re.compile(r'[MmLlHhVvCcSsQqTtAaZz]|-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?')

def draw_path(cr,d):
    """Small SVG path reader for cairo: M L H V C S Q T A Z, absolute and relative."""
    toks=_TOKEN.findall(d);i=0;x=y=sx=sy=cx=cy=0.0;cmd=last=''
    def num():
        nonlocal i;v=float(toks[i]);i+=1;return v
    while i<len(toks):
        if toks[i][0].isalpha():cmd=toks[i];i+=1
        if cmd in 'zZ':cr.close_path();x,y=sx,sy;last=cmd;continue
        rel=cmd.islower();C=cmd.upper();ox,oy=(x,y) if rel else (0,0)
        if C=='M':x,y=ox+num(),oy+num();cr.move_to(x,y);sx,sy=x,y;cmd='l' if rel else 'L'
        elif C=='L':x,y=ox+num(),oy+num();cr.line_to(x,y)
        elif C=='H':x=(x if rel else 0)+num();cr.line_to(x,y)
        elif C=='V':y=(y if rel else 0)+num();cr.line_to(x,y)
        elif C=='C':x1,y1,x2,y2=ox+num(),oy+num(),ox+num(),oy+num();x,y=ox+num(),oy+num();cr.curve_to(x1,y1,x2,y2,x,y);cx,cy=x2,y2
        elif C=='S':
            x1,y1=(2*x-cx,2*y-cy) if last.upper() in 'CS' and last else (x,y);x2,y2=ox+num(),oy+num();x,y=ox+num(),oy+num();cr.curve_to(x1,y1,x2,y2,x,y);cx,cy=x2,y2
        elif C=='Q':
            qx,qy=ox+num(),oy+num();nx,ny=ox+num(),oy+num();cr.curve_to(x+2/3*(qx-x),y+2/3*(qy-y),nx+2/3*(qx-nx),ny+2/3*(qy-ny),nx,ny);x,y=nx,ny;cx,cy=qx,qy
        elif C=='T':
            qx,qy=(2*x-cx,2*y-cy) if last and last.upper() in 'QT' else (x,y);nx,ny=ox+num(),oy+num();cr.curve_to(x+2/3*(qx-x),y+2/3*(qy-y),nx+2/3*(qx-nx),ny+2/3*(qy-ny),nx,ny);x,y=nx,ny;cx,cy=qx,qy
        elif C=='A':
            rx,ry=abs(num()),abs(num());num();large,sweep=num()!=0,num()!=0;ex,ey=ox+num(),oy+num();_arc(cr,x,y,ex,ey,rx,ry,large,sweep);x,y=ex,ey
        else:i+=1
        last=cmd

def _arc(cr,x1,y1,x2,y2,rx,ry,large,sweep):
    if rx==0 or ry==0:cr.line_to(x2,y2);return
    dx,dy=(x1-x2)/2,(y1-y2)/2;l=dx*dx/(rx*rx)+dy*dy/(ry*ry)
    if l>1:rx*=math.sqrt(l);ry*=math.sqrt(l)
    num=rx*rx*ry*ry-rx*rx*dy*dy-ry*ry*dx*dx;den=rx*rx*dy*dy+ry*ry*dx*dx;co=math.sqrt(max(0,num/den))*(-1 if large==sweep else 1)
    cxp,cyp=co*rx*dy/ry,-co*ry*dx/rx;cx,cy=cxp+(x1+x2)/2,cyp+(y1+y2)/2
    a1=math.atan2((dy-cyp)/ry,(dx-cxp)/rx);a2=math.atan2((-dy-cyp)/ry,(-dx-cxp)/rx)
    cr.save();cr.translate(cx,cy);cr.scale(rx,ry)
    (cr.arc if sweep else cr.arc_negative)(0,0,1,a1,a2);cr.restore()

def icon(name,color,size=20,scale=2):
    s=cairo.ImageSurface(cairo.FORMAT_ARGB32,size*scale,size*scale);cr=cairo.Context(s);cr.scale(size*scale/24,size*scale/24)
    draw_path(cr,ICONS.get(name,''));cr.set_source_rgb(*rgb(color));cr.fill()
    s.set_device_scale(scale,scale);img=Gtk.Image.new_from_surface(s);return img

def pie_logo(size=40,scale=2):
    """The app's mark: a pie with one coral slice pulled out, on a lavender tile."""
    s=cairo.ImageSurface(cairo.FORMAT_ARGB32,size*scale,size*scale);cr=cairo.Context(s);cr.scale(size*scale/108,size*scale/108)
    g=cairo.LinearGradient(0,0,108,108);g.add_color_stop_rgb(0,*rgb('#7c6cf0'));g.add_color_stop_rgb(1,*rgb('#4838be'))
    r=24;cr.new_sub_path();cr.arc(108-r,r,r,-math.pi/2,0);cr.arc(108-r,108-r,r,0,math.pi/2);cr.arc(r,108-r,r,math.pi/2,math.pi);cr.arc(r,r,r,math.pi,1.5*math.pi);cr.close_path();cr.set_source(g);cr.fill()
    cx,cy,R=52.2,55.8,34
    for a0,a1,col,push in [(-20,100,'#ffffff',2.0),(100,200,'#ece9ff',2.0),(200,270,'#d0caff',2.0),(-90,-20,None,8.5)]:
        mid=math.radians((a0+a1)/2);x=cx+math.cos(mid)*push;y=cy+math.sin(mid)*push
        cr.move_to(x,y);cr.arc(x,y,R,math.radians(a0),math.radians(a1));cr.close_path()
        if col:cr.set_source_rgb(*rgb(col))
        else:
            lg=cairo.LinearGradient(x,y-R,x+R,y);lg.add_color_stop_rgb(0,*rgb('#ffaa6e'));lg.add_color_stop_rgb(1,*rgb('#ff6278'));cr.set_source(lg)
        cr.fill()
    s.set_device_scale(scale,scale);return Gtk.Image.new_from_surface(s)

def pixbuf_surface(path,max_side=1600):
    pb=GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path),max_side,max_side,True)
    return pb

# ---------------------------------------------------------------- custom widgets
def _round_rect(cr,x,y,w,h,r):
    cr.new_sub_path();cr.arc(x+w-r,y+r,r,-math.pi/2,0);cr.arc(x+w-r,y+h-r,r,0,math.pi/2);cr.arc(x+r,y+h-r,r,math.pi/2,math.pi);cr.arc(x+r,y+r,r,math.pi,1.5*math.pi);cr.close_path()

class Donut(Gtk.DrawingArea):
    """Ring of output formats: click a slice to choose it; click the centre to turn to the other
    side. The mouse wheel is left to the page, which scrolls over it."""
    def __init__(self,p,front,back,selected,title,hint,show_back,chosen,flipped):
        super().__init__();self.p=p;self.front=front;self.back=back;self.selected=selected;self.title=title;self.hint=hint;self.show_back=show_back
        self.chosen=chosen;self.flipped=flipped;self.hover=-1;self.appear=1.0
        self.set_size_request(320,320);self.set_hexpand(True)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK|Gdk.EventMask.BUTTON_RELEASE_MASK|Gdk.EventMask.POINTER_MOTION_MASK|Gdk.EventMask.LEAVE_NOTIFY_MASK)
        self.connect('draw',self.on_draw);self.connect('button-release-event',self.on_click);self.connect('motion-notify-event',self.on_motion)
        self.connect('leave-notify-event',lambda *_:self.set_hover(-1))
    def items(self):return self.back if self.show_back and self.back else self.front
    def geo(self):
        w,h=self.get_allocated_width(),self.get_allocated_height();R=min(w,h)/2-14;return w/2,h/2,R,R*0.47
    def hit(self,x,y):
        cx,cy,R,r=self.geo();d=math.hypot(x-cx,y-cy)
        if d<r-6:return -2
        if d>R+6:return -1
        it=self.items()
        if not it:return -1
        step=360/len(it);a=(math.degrees(math.atan2(y-cy,x-cx))+90+step/2)%360;return int(a/step)%len(it)
    def set_hover(self,h):
        if h!=self.hover:self.hover=h;self.queue_draw()
        win=self.get_window()
        if win:win.set_cursor(Gdk.Cursor.new_from_name(self.get_display(),'pointer' if h>=0 or (h==-2 and self.back) else 'default'))
    def on_motion(self,w,e):self.set_hover(self.hit(e.x,e.y))
    def on_click(self,w,e):
        h=self.hit(e.x,e.y)
        if h>=0:self.selected=self.items()[h];self.queue_draw();self.chosen(self.selected)
        elif h==-2 and self.back:self.flip()
    def flip(self):self.show_back=not self.show_back;self.animate();self.flipped(self.show_back)
    def animate(self):
        self.appear=0.0
        def step():
            self.appear=min(1.0,self.appear+0.12);self.queue_draw();return self.appear<1.0
        GLib.timeout_add(16,step)
    def on_draw(self,w,cr):
        p=self.p;it=self.items();cx,cy,R,r=self.geo();k=0.94+0.06*self.appear
        cr.translate(cx,cy);cr.scale(k,k);cr.translate(-cx,-cy)
        for i in range(8,0,-1):
            cr.set_source_rgba(0.18,0.12,0.4,0.012 if not p['dark'] else 0.05);cr.arc(cx,cy+4,R+4+i,0,2*math.pi);cr.fill()
        cr.set_source_rgb(*rgb(p['surface']));cr.arc(cx,cy,R+4,0,2*math.pi);cr.fill()
        n=max(1,len(it));step=2*math.pi/n;gap=math.radians(2.2) if len(it)>1 else 0
        for i,f in enumerate(it):
            a0=-math.pi/2-step/2+i*step+gap/2;a1=a0+step-gap
            cr.new_path();cr.arc(cx,cy,R,a0,a1);cr.arc_negative(cx,cy,r,a1,a0);cr.close_path()
            sel=f==self.selected;col=p['accent'] if sel else blend(p['segment'],p['accent'],0.16) if i==self.hover else p['segment']
            cr.set_source_rgba(*rgb(col),self.appear);cr.fill_preserve();cr.set_source_rgb(*rgb(p['surface']));cr.set_line_width(3);cr.stroke()
            mid=-math.pi/2+i*step;lr=(R+r)/2;tx,ty=cx+math.cos(mid)*lr,cy+math.sin(mid)*lr
            self.text(cr,f,tx,ty,13.5 if n>9 else 15,p['on_accent'] if sel else p['text'],True)
        cr.set_source_rgb(*rgb(p['border']));cr.arc(cx,cy,r-4,0,2*math.pi);cr.fill()
        cr.set_source_rgb(*rgb(p['surface']));cr.arc(cx,cy,r-9,0,2*math.pi);cr.fill()
        self.text(cr,self.title,cx,cy-8,18,p['text'],True,(r-14)*1.8);self.text(cr,self.hint,cx,cy+14,12,p['muted'],False,(r-14)*1.8)
    def text(self,cr,s,x,y,size,color,bold,fit=None):
        layout=self.create_pango_layout(s);from gi.repository import Pango
        while True:
            fd=Pango.FontDescription.from_string(('Sans Bold ' if bold else 'Sans ')+str(size));layout.set_font_description(fd)
            w,h=layout.get_pixel_size()
            if not fit or w<=fit or size<=9:break
            size-=1
        cr.move_to(x-w/2,y-h/2);cr.set_source_rgb(*rgb(color))
        from gi.repository import PangoCairo;PangoCairo.show_layout(cr,layout)

class Picture(Gtk.DrawingArea):
    """Plain picture, area selection (watermarks) or a before/after comparison slider."""
    VIEW,SELECT,COMPARE=0,1,2
    def __init__(self,p,pixbuf,mode=0,regions=None,after=None,labels=('',''),changed=None,height=360):
        super().__init__();self.p=p;self.pb=pixbuf;self.after=after;self.mode=mode;self.regions=[list(r) for r in (regions or [])];self.active=len(self.regions)-1
        self.labels=labels;self.changed=changed;self.split=0.5;self.drag=0;self.max_h=height
        self.set_hexpand(True);self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK|Gdk.EventMask.BUTTON_RELEASE_MASK|Gdk.EventMask.POINTER_MOTION_MASK|Gdk.EventMask.BUTTON_MOTION_MASK)
        self.connect('draw',self.on_draw);self.connect('button-press-event',self.on_press);self.connect('motion-notify-event',self.on_move);self.connect('button-release-event',self.on_release)
        self.connect('size-allocate',self.on_size)
        self.fade_from=None;self.fade=1.0
        self.set_size_request(-1,220)
    def crossfade(self,pixbuf):
        """Shows another picture (next page, another frame) by fading it in over the current one."""
        if self.pb is None:self.pb=pixbuf;self.queue_resize();self.queue_draw();return
        self.fade_from=self.pb;self.pb=pixbuf;self.fade=0.0;self.queue_resize()
        def step():
            self.fade=min(1.0,self.fade+0.09);self.queue_draw()
            if self.fade>=1.0:self.fade_from=None;return False
            return True
        GLib.timeout_add(16,step)
    def on_size(self,w,a):
        if self.pb is None:return
        want=int(max(160,min(self.max_h,a.width*self.pb.get_height()/max(1,self.pb.get_width()))))
        if abs(want-a.height)>2:GLib.idle_add(self.set_size_request,-1,want)
    def frame(self):
        W,H=self.get_allocated_width(),self.get_allocated_height()
        if self.pb is None:return 0,0,W,H
        s=min(W/self.pb.get_width(),H/self.pb.get_height());w,h=self.pb.get_width()*s,self.pb.get_height()*s;return (W-w)/2,(H-h)/2,w,h
    def on_draw(self,w,cr):
        p=self.p;W,H=self.get_allocated_width(),self.get_allocated_height()
        _round_rect(cr,0,0,W,H,14);cr.clip();cr.set_source_rgb(*rgb('#0e0d12' if p['dark'] else '#e9e7ef'));cr.paint()
        if self.pb is None:return
        fx,fy,fw,fh=self.frame()
        def paint(pb,clip=None,alpha=1.0):
            cr.save()
            if clip:cr.rectangle(*clip);cr.clip()
            cr.translate(fx,fy);cr.scale(fw/pb.get_width(),fh/pb.get_height());Gdk.cairo_set_source_pixbuf(cr,pb,0,0);cr.get_source().set_filter(cairo.FILTER_GOOD)
            if alpha<1.0:cr.paint_with_alpha(alpha)
            else:cr.paint()
            cr.restore()
        if self.mode==self.COMPARE and self.after is not None:
            x=fx+fw*self.split;paint(self.pb,(fx,fy,x-fx,fh));paint(self.after,(x,fy,fx+fw-x,fh))
            cr.set_source_rgb(1,1,1);cr.set_line_width(2.5);cr.move_to(x,fy);cr.line_to(x,fy+fh);cr.stroke()
            cr.arc(x,H/2,15,0,2*math.pi);cr.fill();cr.set_source_rgb(*rgb(p['accent']));cr.arc(x,H/2,11,0,2*math.pi);cr.fill()
            self.pill(cr,self.labels[0],fx+10,fy+fh-34,False);self.pill(cr,self.labels[1],fx+fw-10,fy+fh-34,True)
        elif self.fade_from is not None and self.fade<1.0:paint(self.fade_from);paint(self.pb,alpha=self.fade)
        else:paint(self.pb)
        if self.mode==self.SELECT and self.regions:
            cr.set_fill_rule(cairo.FILL_RULE_EVEN_ODD);cr.rectangle(fx,fy,fw,fh)
            for r in self.regions:cr.rectangle(*self.view(r))
            cr.set_source_rgba(0,0,0,0.33);cr.fill();cr.set_fill_rule(cairo.FILL_RULE_WINDING)
            for i,r in enumerate(self.regions):
                x,y,w,h=self.view(r);on=i==self.active;cr.set_source_rgb(*rgb(p['accent'] if on else '#ffffff'));cr.set_line_width(2.5 if on else 1.5);_round_rect(cr,x,y,w,h,4);cr.stroke()
                if on:
                    for kx,ky in [(x,y),(x+w,y),(x,y+h),(x+w,y+h)]:
                        cr.set_source_rgb(1,1,1);cr.arc(kx,ky,8,0,2*math.pi);cr.fill();cr.set_source_rgb(*rgb(p['accent']));cr.arc(kx,ky,5,0,2*math.pi);cr.fill()
    def pill(self,cr,s,x,y,right):
        if not s:return
        layout=self.create_pango_layout(s);from gi.repository import Pango,PangoCairo
        layout.set_font_description(Pango.FontDescription.from_string('Sans Bold 10'));tw,th=layout.get_pixel_size();w,h=tw+18,24
        x0=x-w if right else x;cr.set_source_rgba(0,0,0,0.62);_round_rect(cr,x0,y,w,h,12);cr.fill();cr.set_source_rgb(1,1,1);cr.move_to(x0+9,y+(h-th)/2);PangoCairo.show_layout(cr,layout)
    def view(self,r):
        fx,fy,fw,fh=self.frame();return fx+r[0]*fw,fy+r[1]*fh,r[2]*fw,r[3]*fh
    def norm(self,x,y):
        fx,fy,fw,fh=self.frame();return max(0,min(1,(x-fx)/max(1,fw))),max(0,min(1,(y-fy)/max(1,fh)))
    def on_press(self,w,e):
        if self.mode==self.COMPARE:self.split=self.norm(e.x,e.y)[0];self.queue_draw();return True
        if self.mode!=self.SELECT or self.pb is None:return False
        self.down=self.norm(e.x,e.y);self.drag=0
        for i in range(len(self.regions)-1,-1,-1):
            x,y,ww,hh=self.view(self.regions[i])
            for k,(kx,ky) in enumerate([(x,y),(x+ww,y),(x,y+hh),(x+ww,y+hh)],1):
                if math.hypot(e.x-kx,e.y-ky)<14:self.drag=k;break
            if not self.drag and x<=e.x<=x+ww and y<=e.y<=y+hh:self.drag=5
            if self.drag:self.active=i;self.start=list(self.regions[i]);break
        if not self.drag:
            if len(self.regions)>=4:self.regions.pop(0)
            self.regions.append([self.down[0],self.down[1],0,0]);self.active=len(self.regions)-1;self.start=list(self.regions[-1]);self.drag=6
        self.queue_draw();return True
    def on_move(self,w,e):
        if self.mode==self.COMPARE and e.state&Gdk.ModifierType.BUTTON1_MASK:self.split=self.norm(e.x,e.y)[0];self.queue_draw();return True
        if not self.drag or self.active<0:return False
        nx,ny=self.norm(e.x,e.y);s=self.start;l,t,rr,b=s[0],s[1],s[0]+s[2],s[1]+s[3]
        if self.drag==5:dx,dy=nx-self.down[0],ny-self.down[1];l=max(0,min(1-s[2],l+dx));t=max(0,min(1-s[3],t+dy));rr,b=l+s[2],t+s[3]
        elif self.drag==6:l,t,rr,b=min(s[0],nx),min(s[1],ny),max(s[0],nx),max(s[1],ny)
        else:
            if self.drag in (1,3):l=min(rr-0.01,nx)
            if self.drag in (2,4):rr=max(l+0.01,nx)
            if self.drag in (1,2):t=min(b-0.01,ny)
            if self.drag in (3,4):b=max(t+0.01,ny)
        self.regions[self.active]=[l,t,rr-l,b-t];self.queue_draw();return True
    def on_release(self,w,e):
        if self.mode!=self.SELECT:return False
        if self.drag==6 and 0<=self.active<len(self.regions):
            r=self.regions[self.active]
            if r[2]<0.015 or r[3]<0.015:self.regions.pop(self.active);self.active=len(self.regions)-1
        self.drag=0;self.queue_draw()
        if self.changed:self.changed([list(r) for r in self.regions])
        return True

class Wave(Gtk.DrawingArea):
    def __init__(self,p,peaks,height=64):
        super().__init__();self.p=p;self.peaks=peaks or [];self.set_size_request(-1,height);self.set_hexpand(True);self.connect('draw',self.on_draw)
    def on_draw(self,w,cr):
        W,H=self.get_allocated_width(),self.get_allocated_height();n=len(self.peaks)
        if not n:cr.set_source_rgb(*rgb(self.p['border']));cr.rectangle(0,H/2-1,W,2);cr.fill();return
        bar=W/n;bw=max(1.5,bar*0.62);played=getattr(self,'played',1.0)
        for i,v in enumerate(self.peaks):
            cr.set_source_rgb(*rgb(self.p['accent'] if (i+0.5)/n<=played else blend(self.p['muted'],self.p['surface'],0.45)))
            h=max(2,v*(H-6));x=i*bar+(bar-bw)/2;_round_rect(cr,x,H/2-h/2,bw,h,min(bw/2,h/2));cr.fill()

class Flow(Gtk.FlowBox):
    """Chips that wrap onto new lines."""
    def __init__(self):
        super().__init__();self.set_selection_mode(Gtk.SelectionMode.NONE);self.set_column_spacing(8);self.set_row_spacing(8);self.set_homogeneous(False);self.set_max_children_per_line(30);self.set_valign(Gtk.Align.START)
    def add_child(self,w):
        self.add(w);child=w.get_parent();child.set_can_focus(False);return w


def clock(s,tenths=False):
    s=max(0.0,s or 0.0);h,rest=divmod(s,3600);m,sec=divmod(rest,60)
    sec_text=f'{sec:04.1f}' if tenths else f'{int(sec):02}'
    return (f'{int(h)}:{int(m):02}:' if h>=1 else f'{int(m)}:')+sec_text

class Player(Gtk.Box):
    """Plays a video or sound inside the window with the bundled FFmpeg: picture frames come
    through a pipe, the sound goes to PulseAudio/PipeWire. Play/pause, seek bar and time."""
    live=set()
    def __init__(self,p,path,duration,size=None,poster=None,peaks=None,marks=None,labels=('','','','')):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,spacing=8);Player.live.add(self)
        from . import runtime
        self.p=p;self.path=str(path);self.duration=max(0.1,float(duration or 0.1));self.video=size is not None;self.marks=marks
        self.ffmpeg=runtime.tool_path('ffmpeg') or 'ffmpeg';self.env=runtime.process_env()
        self.pos=0.0;self.playing=False;self.procs=[];self.token=0;self.started=0.0;self.start_pos=0.0;self.pending=False
        if self.video:
            w,h=size;scale=min(1.0,960/max(1,w));self.fw=max(2,int(w*scale)//2*2);self.fh=max(2,int(h*scale)//2*2)
            self.view=Picture(p,poster,height=440);self.add(self.view)
            ev=self.view;ev.add_events(Gdk.EventMask.BUTTON_RELEASE_MASK);ev.connect('button-release-event',lambda *a:self.toggle())
        else:
            self.view=Wave(p,peaks or [],72);self.view.played=0.0;self.add(self.view)
        bar=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=8)
        self.button=Gtk.Button();self.button.get_style_context().add_class('icon');self.button.add(icon('play',p['accent_text'],24));self.button.connect('clicked',lambda *a:self.toggle());bar.add(self.button)
        self.scale=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,0,self.duration,0.1);self.scale.set_draw_value(False);self.scale.set_hexpand(True)
        self.scale.connect('change-value',self.on_seek);bar.pack_start(self.scale,True,True,0)
        self.time=Gtk.Label(label=f'{clock(0)} / {clock(self.duration)}');self.time.get_style_context().add_class('small');bar.add(self.time);self.add(bar)
        self.mark_row=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=8);self.mark_row.set_no_show_all(True)
        if marks:
            for key,text in (('start',labels[0]),('end',labels[1])):
                b=Gtk.Button(label=text);b.get_style_context().add_class('chip');b.connect('clicked',lambda _b,k=key:marks(k,self.position()));b.show();self.mark_row.add(b)
        self.add(self.mark_row)
        GLib.timeout_add(120,self.tick);self.connect('destroy',lambda *a:self.stop())
    def show_marks(self,on):self.mark_row.set_visible(bool(on and self.marks))
    def position(self):return min(self.duration,self.start_pos+(time.monotonic()-self.started)) if self.playing else self.pos
    def set_icon(self,name):
        for c in self.button.get_children():self.button.remove(c)
        self.button.add(icon(name,self.p['accent_text'],24));self.button.show_all()
    def toggle(self):
        if self.playing:self.pause()
        else:
            if self.pos>=self.duration-0.05:self.pos=0.0
            self.play()
        return True
    def play(self):
        self.stop_processes();self.token+=1;token=self.token;at=f'{self.pos:.3f}';base=[self.ffmpeg,'-hide_banner','-loglevel','error','-nostdin','-ss',at]
        try:
            self.procs.append(subprocess.Popen([*base,'-i',self.path,'-vn','-f','pulse','-name','Dönüştürücü','default'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=self.env))
        except OSError:pass
        if self.video:
            proc=subprocess.Popen([*base,'-re','-i',self.path,'-an','-sn','-vf',f'scale={self.fw}:{self.fh}','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=self.env)
            self.procs.append(proc);threading.Thread(target=self.read_frames,args=(proc,token),daemon=True).start()
        self.playing=True;self.started=time.monotonic();self.start_pos=self.pos;self.set_icon('pause')
    def read_frames(self,proc,token):
        size=self.fw*self.fh*3
        while token==self.token:
            data=proc.stdout.read(size)
            if len(data)<size:break
            if not self.pending:self.pending=True;GLib.idle_add(self.show_frame,token,data)
    def show_frame(self,token,data):
        self.pending=False
        if token==self.token:
            pb=GdkPixbuf.Pixbuf.new_from_bytes(GLib.Bytes.new(data),GdkPixbuf.Colorspace.RGB,False,8,self.fw,self.fh,self.fw*3)
            self.view.pb=pb;self.view.queue_draw()
        return False
    def still(self,at):
        """The picture at a moment while paused (after seeking)."""
        self.token+=1;token=self.token
        def work():
            try:
                r=subprocess.run([self.ffmpeg,'-hide_banner','-loglevel','error','-nostdin','-ss',f'{at:.3f}','-i',self.path,'-frames:v','1','-an','-vf',f'scale={self.fw}:{self.fh}','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],capture_output=True,env=self.env,timeout=20)
                if len(r.stdout)>=self.fw*self.fh*3:GLib.idle_add(self.show_frame,token,r.stdout[:self.fw*self.fh*3])
            except Exception:pass
        threading.Thread(target=work,daemon=True).start()
    def pause(self):
        self.pos=self.position();self.stop_processes();self.playing=False;self.set_icon('play')
    def on_seek(self,scale,scroll,value):
        self.pos=max(0.0,min(self.duration,value))
        if self.playing:self.play()
        elif self.video:self.still(self.pos)
        self.update();return False
    def update(self):
        pos=self.position();self.scale.set_value(pos);self.time.set_text(f'{clock(pos,True)} / {clock(self.duration)}')
        if not self.video:self.view.played=pos/self.duration;self.view.queue_draw()
    def tick(self):
        if self not in Player.live:return False
        if self.playing:
            if self.position()>=self.duration-0.02 or all(p.poll() is not None for p in self.procs):
                self.pos=self.duration if self.position()>=self.duration-0.3 else self.position();self.stop_processes();self.playing=False;self.set_icon('play')
            self.update()
        return True
    def stop_processes(self):
        self.token+=1
        for proc in self.procs:
            try:proc.terminate()
            except Exception:pass
        self.procs=[]
    def stop(self):
        if self.playing:self.pause()
        self.stop_processes();Player.live.discard(self)
    @classmethod
    def stop_all(cls):
        for player in list(cls.live):player.stop()
