#!/usr/bin/env python3
"""Windows/macOS: standart Tk. Linux: GTK varsa GTK, yoksa Tk."""
import sys
if sys.platform.startswith('linux') and '--portable-ui' not in sys.argv:
    try:import gi;gi.require_version('Gtk','3.0')
    except (ImportError,ValueError):from donusturucu.portable import main
    else:from donusturucu.app import main
else:
    if '--portable-ui' in sys.argv:sys.argv.remove('--portable-ui')
    from donusturucu.portable import main
main()
