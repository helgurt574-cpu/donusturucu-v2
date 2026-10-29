"""Light/dark palettes and system color-scheme detection shared by the GTK and Tk windows."""
import json
import os
import shutil
import subprocess
import sys
from . import runtime

MODES=('system','light','dark')

PALETTES={
 'light':{
  'bg':'#f4f6fb','surface':'#ffffff','surface2':'#f0f3f9','surface3':'#e6ebf4','border':'#dfe5ef','text':'#17253b','muted':'#5b6980',
  'accent':'#3b5bdb','accent_hover':'#3250c4','accent_active':'#2a45ad','accent_fg':'#ffffff','accent_soft':'#e7ecff','accent_soft_fg':'#2440a8',
  'success':'#13795c','success_soft':'#e3f4ec','danger':'#a51d2d','danger_soft':'#fff0f1','danger_border':'#e3aab2','danger_active':'#fbd9de',
  'warning':'#8a5a00','warning_soft':'#fff4dc','info':'#3b5bdb',
  'disabled_bg':'#edf0f5','disabled_fg':'#4d5b70','drop':'#eef2ff','drop_border':'#b7c5ed','drop_hover':'#dfe7ff',
  'selection':'#e3e9ff','selection_fg':'#1e3a99','shadow':'rgba(23,37,59,0.06)','trough':'#e4e9f3',
 },
 'dark':{
  'bg':'#13151b','surface':'#1c1f27','surface2':'#252a34','surface3':'#2e3440','border':'#323846','text':'#e7eaf1','muted':'#a0a9ba',
  'accent':'#4263eb','accent_hover':'#5272f0','accent_active':'#3654d1','accent_fg':'#ffffff','accent_soft':'#262f52','accent_soft_fg':'#b9c7ff',
  'success':'#5fd3a5','success_soft':'#173328','danger':'#ffb3bd','danger_soft':'#3a1d23','danger_border':'#6b2f39','danger_active':'#4a232b',
  'warning':'#f5c264','warning_soft':'#3a2e14','info':'#8ea4ff',
  'disabled_bg':'#252a34','disabled_fg':'#9aa3b5','drop':'#1a2036','drop_border':'#3a4878','drop_hover':'#222b4a',
  'selection':'#2b3765','selection_fg':'#e2e8ff','shadow':'rgba(0,0,0,0.35)','trough':'#2a303c',
 },
}

def settings_path():return runtime.config_dir()/'settings.json'

def load_settings():
    try:return json.loads(settings_path().read_text(encoding='utf-8'))
    except (OSError,ValueError):return {}

def stored_mode():
    mode=load_settings().get('theme','system')
    return mode if mode in MODES else 'system'

def _name_is_dark(name):
    name=(name or '').lower()
    return 'dark' in name or 'black' in name or name.endswith(':dark')

def _run(args):
    if not shutil.which(args[0]):return ''
    try:return subprocess.run(args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=2,text=True).stdout.strip().strip("'")
    except (OSError,subprocess.TimeoutExpired):return ''

def _portal_scheme():
    """org.freedesktop.appearance color-scheme: 1 dark, 2 light, 0/None no preference."""
    try:
        from gi.repository import Gio,GLib
        bus=Gio.bus_get_sync(Gio.BusType.SESSION,None)
        reply=bus.call_sync('org.freedesktop.portal.Desktop','/org/freedesktop/portal/desktop','org.freedesktop.portal.Settings','Read',
            GLib.Variant('(ss)',('org.freedesktop.appearance','color-scheme')),None,Gio.DBusCallFlags.NONE,800,None)
        value=reply.unpack()[0]
        while isinstance(value,(GLib.Variant,tuple)):value=value.unpack() if isinstance(value,GLib.Variant) else value[0]
        return int(value)
    except Exception:return None

def _gnome_scheme():
    try:
        from gi.repository import Gio
        source=Gio.SettingsSchemaSource.get_default()
        schema=source.lookup('org.gnome.desktop.interface',True) if source else None
        if schema and schema.has_key('color-scheme'):return Gio.Settings.new('org.gnome.desktop.interface').get_string('color-scheme')
        return None
    except Exception:return _run(['gsettings','get','org.gnome.desktop.interface','color-scheme']) or None

def system_theme_name():
    """The desktop's GTK theme name, read below any in-app override."""
    try:
        import gi
        gi.require_version('Gdk','3.0')
        from gi.repository import Gdk,GObject
        screen=Gdk.Screen.get_default()
        if screen:
            value=GObject.Value(str)
            if screen.get_setting('gtk-theme-name',value) and value.get_value():return value.get_value()
    except Exception:pass
    return _run(['xfconf-query','-c','xsettings','-p','/Net/ThemeName']) or _run(['gsettings','get','org.gnome.desktop.interface','gtk-theme'])

_UNREAD=object()

def _windows_dark():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize') as key:
            return winreg.QueryValueEx(key,'AppsUseLightTheme')[0]==0
    except OSError:return False

def _macos_dark():
    # 'Dark' when the appearance is dark (also while Auto has switched to dark).
    return _run(['defaults','read','-g','AppleInterfaceStyle']).lower()=='dark'

def system_prefers_dark(portal=_UNREAD):
    """`portal` lets a GUI pass its cached portal value instead of a D-Bus round trip."""
    if sys.platform=='win32':return _windows_dark()
    if sys.platform=='darwin':return _macos_dark()
    if _name_is_dark(os.environ.get('GTK_THEME')):return True
    if portal is _UNREAD:portal=_portal_scheme()
    # Any dark signal wins: XFCE/MATE only rename the GTK theme, GNOME/KDE set a color scheme.
    if portal==1 or _gnome_scheme()=='prefer-dark':return True
    return _name_is_dark(system_theme_name())

def resolve(mode,portal=_UNREAD):
    if mode=='light' or mode=='dark':return mode
    return 'dark' if system_prefers_dark(portal) else 'light'

GTK_CSS='''
window, dialog, .background { background-color: @bg; color: @text; }
headerbar { background-image: none; background-color: @surface; border-bottom: 1px solid @border; box-shadow: none; color: @text; min-height: 46px; }
headerbar .title { font-weight: 700; }
popover, popover.background { background-color: @surface; border: 1px solid @border; border-radius: 12px; color: @text; }
popover modelbutton, popover .menu-row { padding: 6px 10px; border-radius: 7px; }
popover modelbutton:hover { background-color: @surface2; }
.menu-heading { color: @muted; font-size: 11px; font-weight: 700; margin-top: 4px; }
.hero-title { font-size: 30px; font-weight: 800; letter-spacing: -0.5px; color: @text; }
.subtitle, .hint { color: @muted; }
.subtitle { font-size: 13px; }
.hint { font-size: 11px; }
.section { font-size: 15px; font-weight: 700; color: @text; }
.badge { color: @success; background-color: @success_soft; border-radius: 999px; padding: 6px 12px; font-size: 10px; font-weight: 700; }
.card { background-color: @surface; border: 1px solid @border; border-radius: 14px; padding: 18px; box-shadow: 0 1px 3px @shadow; }
.drop { background-color: @drop; border: 2px dashed @drop_border; border-radius: 14px; padding: 18px; }
.drop.drop-hover { background-color: @drop_hover; border-color: @accent; border-style: solid; }
.drop image { color: @accent; }
.empty-title { font-size: 15px; font-weight: 700; color: @text; }
.empty-icon { color: @muted; opacity: 0.6; }
button { background-image: none; background-color: @surface2; color: @text; border: 1px solid @border; border-radius: 9px; padding: 7px 13px; box-shadow: none; text-shadow: none; -gtk-icon-shadow: none; }
button:hover { background-color: @surface3; }
button:active, button:checked { background-color: @surface3; border-color: @accent; }
button:disabled { background-color: @disabled_bg; color: @disabled_fg; border-color: @border; }
button:disabled label { color: @disabled_fg; }
button.flat, headerbar button.flat { background-color: transparent; border-color: transparent; }
button.flat:hover, headerbar button.flat:hover { background-color: @surface2; }
button.suggested-action { background-color: @accent; color: @accent_fg; border-color: @accent; font-weight: 700; }
button.suggested-action label, button.suggested-action image { color: @accent_fg; }
button.suggested-action:hover { background-color: @accent_hover; border-color: @accent_hover; }
button.suggested-action:active { background-color: @accent_active; }
button.suggested-action:disabled { background-color: @disabled_bg; color: @disabled_fg; border-color: @border; }
button.suggested-action:disabled label { color: @disabled_fg; }
button.stop-action, button.stop-action:hover, button.stop-action:focus { background-image: none; background-color: @danger_soft; color: @danger; border: 1px solid @danger_border; text-shadow: none; box-shadow: none; }
button.stop-action label, button.stop-action image { color: @danger; }
button.stop-action:active { background-image: none; background-color: @danger_active; color: @danger; }
button.stop-action:disabled { background-image: none; background-color: @disabled_bg; color: @disabled_fg; border-color: @border; }
button.stop-action:disabled label { color: @disabled_fg; }
.linked button.mode-button:checked { background-color: @accent_soft; color: @accent_soft_fg; border-color: @accent; font-weight: 700; }
.linked button.mode-button:checked label { color: @accent_soft_fg; }
combobox button, combobox button.combo { padding: 6px 10px; }
entry { background-image: none; background-color: @surface; color: @text; border: 1px solid @border; border-radius: 9px; padding: 6px 9px; box-shadow: none; }
entry:focus { border-color: @accent; }
checkbutton { color: @text; }
check { background-image: none; background-color: @surface; border: 1px solid @border; border-radius: 5px; min-width: 16px; min-height: 16px; }
check:checked { background-color: @accent; border-color: @accent; color: @accent_fg; -gtk-icon-source: -gtk-icontheme("object-select-symbolic"); }
treeview.view { background-color: @surface; color: @text; }
treeview.view:hover { background-color: @surface2; }
treeview.view:selected, treeview.view:selected:focus { background-color: @selection; color: @selection_fg; }
treeview.view header button { background-color: @surface2; color: @muted; border: none; border-bottom: 1px solid @border; border-radius: 0; font-weight: 700; font-size: 11px; padding: 7px 8px; }
treeview.view header button:hover { background-color: @surface3; }
scrolledwindow { background-color: transparent; }
scrolledwindow.queue-frame { border: 1px solid @border; border-radius: 10px; }
scrollbar { background-color: transparent; border: none; }
scrollbar slider { background-color: @surface3; border-radius: 999px; min-width: 7px; min-height: 7px; }
scrollbar slider:hover { background-color: @muted; }
progressbar trough { min-height: 8px; border-radius: 8px; background-color: @trough; border: none; }
progressbar progress { min-height: 8px; border-radius: 8px; background-image: none; background-color: @accent; border: none; }
progressbar text { color: @muted; font-size: 11px; }
textview, textview text { background-color: @surface; color: @text; }
tooltip, tooltip.background { background-color: @surface3; color: @text; border-radius: 7px; }
tooltip label { color: @text; }
'''

def gtk_css(name):
    colors=PALETTES[name]
    defines=''.join(f'@define-color {key} {value};\n' for key,value in colors.items())
    return (defines+GTK_CSS).encode()
