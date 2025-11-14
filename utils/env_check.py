import shutil, platform, subprocess, sys
from typing import List
import winreg

class EnvReport:
    def __init__(self):
        self.ok = True
        self.issues: List[str] = []
        self.details: List[str] = []

    def add_issue(self, msg: str):
        self.ok = False
        self.issues.append(msg)

    def add_detail(self, msg: str):
        self.details.append(msg)


def check_environment() -> EnvReport:
    rep = EnvReport()
    # Check Tesseract (optional but recommended)
    if shutil.which('tesseract'):
        rep.add_detail('Tesseract OK')
    else:
        rep.add_issue('Tesseract OCR no encontrado (instala https://github.com/UB-Mannheim/tesseract/wiki).')
    # Check GPU availability (OpenCV) placeholder
    rep.add_detail(f"Python {platform.python_version()} arch={platform.machine()}")
    # Check Visual C++ Redistributable (search common registry key)
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64")
        _ = winreg.QueryValueEx(key, "Installed")
        rep.add_detail('VC++ 2015-2022 Redistributable x64 presente')
    except Exception:
        rep.add_issue('VC++ Redistributable 2015-2022 x64 no detectado (instala https://aka.ms/vcredist).')
    return rep

if __name__ == '__main__':
    r = check_environment()
    if not r.ok:
        print('Problemas detectados:')
        for i in r.issues:
            print('-', i)
        sys.exit(1)
    print('Entorno OK')
