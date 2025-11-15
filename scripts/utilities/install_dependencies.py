
#!/usr/bin/env python3
# Quick installer for GeoDocs Scanner optional features.
import subprocess, sys, os, pathlib
REQ = pathlib.Path(__file__).with_name("requirements.txt")
if not REQ.exists():
    print("requirements.txt not found"); sys.exit(1)
print("Installing dependencies from requirements.txt ...")
cmd = [sys.executable, "-m", "pip", "install", "-r", str(REQ)]
sys.exit(subprocess.call(cmd))
