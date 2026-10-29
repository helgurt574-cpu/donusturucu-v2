import unittest
from donusturucu.i18n import STRINGS

def contrast(fg,bg):
    def lum(color):
        vals=[c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in color]
        return .2126*vals[0]+.7152*vals[1]+.0722*vals[2]
    a,b=sorted([lum(fg),lum(bg)])
    return (b+.05)/(a+.05)

class StopContrastTests(unittest.TestCase):
    def test_tk_stop_states(self):
        import tkinter as tk
        from donusturucu.portable import Window
        root=Window();root.withdraw()
        try:
            for state in [(),('active',),('pressed',),('disabled',),('focus',)]:
                with self.subTest(state=state):
                    fg=root.style.lookup('Stop.TButton','foreground',state=state)
                    bg=root.style.lookup('Stop.TButton','background',state=state)
                    f=[v/65535 for v in root.winfo_rgb(fg)];b=[v/65535 for v in root.winfo_rgb(bg)]
                    self.assertGreaterEqual(contrast(f,b),4.5,(state,fg,bg))
        finally:root.destroy()
    def test_gtk_stop_states(self):
        import gi
        gi.require_version('Gtk','3.0')
        from gi.repository import Gtk
        from donusturucu.app import App,Window
        app=App([]);app.register(None);w=Window(app,[])
        try:
            ctx=w.stop_button.get_style_context()
            for state in [Gtk.StateFlags.NORMAL,Gtk.StateFlags.PRELIGHT,Gtk.StateFlags.ACTIVE,Gtk.StateFlags.INSENSITIVE]:
                w.stop_button.set_sensitive(state!=Gtk.StateFlags.INSENSITIVE)
                w.stop_button.set_state_flags(state,True)
                while Gtk.events_pending():Gtk.main_iteration_do(False)
                fg=ctx.get_color(state);bg=ctx.get_background_color(state)
                self.assertGreaterEqual(contrast([fg.red,fg.green,fg.blue],[bg.red,bg.green,bg.blue]),4.5,str(state))
        finally:w.destroy();app.quit()

if __name__=='__main__':unittest.main(verbosity=2)
