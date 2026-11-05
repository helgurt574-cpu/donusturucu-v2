"""Local-only browser interface; the page and the server live in donusturucu/webapp.py."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from donusturucu.webapp import serve
if __name__=='__main__':serve(desktop=False,open_window='--no-browser' not in sys.argv)
