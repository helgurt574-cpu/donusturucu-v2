"""Native GTK file chooser for the Tk windows on Linux; prints the chosen paths as JSON.

Tk's own Linux dialog has no sidebar, bookmarks, search or theming, so the extras window
asks this helper instead and falls back to Tk when GTK is unavailable.
"""
import argparse,json,sys

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['open','open-multiple','folder'],default='open')
    parser.add_argument('--title',default='');parser.add_argument('--start',default='')
    parser.add_argument('--filter',action='append',default=[],help='Label|*.srt *.ass')
    parser.add_argument('--theme',choices=['light','dark'],default='light')
    parser.add_argument('--accept',default='');parser.add_argument('--cancel',default='')
    args=parser.parse_args()
    import gi
    gi.require_version('Gtk','3.0')
    from gi.repository import Gtk
    settings=Gtk.Settings.get_default()
    settings.props.gtk_theme_name='Adwaita';settings.props.gtk_application_prefer_dark_theme=args.theme=='dark'
    action=Gtk.FileChooserAction.SELECT_FOLDER if args.mode=='folder' else Gtk.FileChooserAction.OPEN
    dialog=Gtk.FileChooserNative.new(args.title,None,action,args.accept or None,args.cancel or None)
    dialog.set_select_multiple(args.mode=='open-multiple')
    for item in args.filter:
        label,_,patterns=item.partition('|');flt=Gtk.FileFilter();flt.set_name(label)
        for pattern in patterns.split():flt.add_pattern(pattern)
        dialog.add_filter(flt)
    if args.start:dialog.set_current_folder(args.start)
    result=dialog.run()
    paths=dialog.get_filenames() if result==Gtk.ResponseType.ACCEPT else []
    print(json.dumps([p for p in paths if p],ensure_ascii=False),flush=True)

if __name__=='__main__':sys.exit(main())
