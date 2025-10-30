
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import sys
# Reutiliza la interfaz completa con todas las funciones (OCR, exportación, IIIF, etc.)
import gui_book_scan_tk

if __name__ == "__main__":
    # Start background quality scheduler
    try:
        from modules.scheduler import SCHEDULER
        SCHEDULER.start()
        print('Quality scheduler started')
    except Exception as ex:
        print('Scheduler not started:', ex)
    gui_book_scan_tk.main()
