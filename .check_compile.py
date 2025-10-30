import py_compile,sys,traceback
p=r'M:\\Trabajo Privado\\FAT\\Book Scanner 3.2\\gui_book_scan_tk.py'
try:
    py_compile.compile(p, doraise=True)
    print('COMPILE_OK')
except Exception:
    print('COMPILE_FAIL')
    traceback.print_exc()
    sys.exit(1)
