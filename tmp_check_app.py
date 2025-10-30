import sys
sys.path.insert(0, r'm:\Trabajo Privado\FAT\Book Scanner 3.2')
import gui_book_scan_tk as g
print('has App', hasattr(g,'App'))
print('App dict keys sample:', sorted([k for k in g.App.__dict__.keys() if not k.startswith('__')])[:40])
