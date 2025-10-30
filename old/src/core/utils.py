#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import platform
import subprocess
import hashlib
from pathlib import Path

def sha256_of_file(path: Path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def list_cameras_with_names(max_devices=10):
    names = {}
    sysname = platform.system().lower()
    
    # Linux
    if sysname == "linux":
        for i in range(max_devices):
            dev = f"/sys/class/video4linux/video{i}/name"
            if os.path.exists(dev):
                try:
                    with open(dev, "r", encoding="utf-8", errors="ignore") as f:
                        names[i] = f.read().strip()
                except:
                    pass
    
    # macOS
    elif sysname == "darwin":
        try:
            text = subprocess.check_output(
                ["system_profiler", "SPCameraDataType"],
                text=True, stderr=subprocess.DEVNULL, timeout=2
            )
            idx = 0
            for line in text.splitlines():
                line = line.strip()
                if (line and not line.startswith("System Information") 
                    and ": " not in line and not line.startswith("Models:")):
                    if idx < max_devices:
                        names[idx] = line
                        idx += 1
        except:
            pass
    
    # Windows
    else:
        try:
            out = subprocess.check_output(
                ["wmic", "path", "Win32_PnPEntity", 
                 "where", "PNPClass='Camera'", "get", "Name"],
                text=True, stderr=subprocess.DEVNULL, timeout=2
            )
            idx = 0
            for line in out.splitlines():
                line = line.strip()
                if line and line.lower() != "name":
                    if idx < max_devices:
                        names[idx] = line
                        idx += 1
        except:
            try:
                out = subprocess.check_output(
                    ["powershell", "-NoProfile",
                     "-Command", 
                     "Get-CimInstance Win32_PnPEntity -Filter \"PNPClass='Camera'\" | Select-Object -ExpandProperty Name"],
                    text=True, stderr=subprocess.DEVNULL, timeout=2
                )
                idx = 0
                for line in out.splitlines():
                    line = line.strip()
                    if line:
                        if idx < max_devices:
                            names[idx] = line
                            idx += 1
            except:
                pass
    
    # Test each camera
    valid = []
    import cv2
    for i in range(max_devices):
        cap = cv2.VideoCapture(
            i, cv2.CAP_DSHOW if sysname=="windows" else 0
        )
        ok, frame = cap.read()
        if ok:
            valid.append(i)
        cap.release()
    
    return [(i, names.get(i, f"Cámara {i}")) for i in valid] or [(0, "Cámara 0")]

def citation_apa(autor, anio, titulo, archivo, fondo, signatura, lugar=None):
    p = []
    if autor:
        p.append(autor)
    if anio:
        p.append(f"({anio}).")
    if titulo:
        p.append(f"*{titulo}*.")
    cola = []
    if archivo:
        cola.append(archivo)
    if fondo:
        cola.append(f"Fondo {fondo}")
    if signatura:
        cola.append(f"Signatura {signatura}")
    if lugar:
        cola.append(lugar)
    if cola:
        p.append(", ".join(cola) + ".")
    return " ".join(p)

def citation_iso690(autor, anio, titulo, lugar, archivo, fondo, signatura):
    p = []
    if autor:
        p.append(autor.upper())
    if anio:
        p.append(f"({anio})")
    if titulo:
        p.append(titulo)
    cola = []
    if lugar:
        cola.append(lugar)
    if archivo:
        cola.append(archivo)
    if fondo:
        cola.append(f"Fondo {fondo}")
    if signatura:
        cola.append(f"Signatura {signatura}")
    if cola:
        p.append(". ".join(cola))
    return ". ".join([x for x in p if x])

def load_profile_file(base_dir: Path, name: str):
    path = base_dir / f"config.{name}.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def activate_profile(base_dir: Path, name: str):
    prof = load_profile_file(base_dir, name)
    if not prof:
        raise RuntimeError(f"Perfil no encontrado: {name}")
    config_path = base_dir / "geodocs_config.json"
    config_path.write_text(json.dumps(prof, indent=2), encoding="utf-8")
    return prof

def try_ping(api):
    try:
        ep = api.map.get("endpoints",{}).get("pull_documents","/api/documentos")
        url_health = api.base() + "/health"
        try:
            r = requests.get(url_health, headers=api.headers(),
                           timeout=3, verify=api.verify())
            if r.status_code < 500:
                return True, "health"
        except Exception:
            pass
        r = requests.get(api.base()+ep, headers=api.headers(),
                        timeout=3, verify=api.verify())
        return (r.status_code < 500), "endpoint"
    except Exception:
        return False, "error"

def detect_environment(base_dir: Path, api_class):
    dev = load_profile_file(base_dir, "dev")
    prod = load_profile_file(base_dir, "prod")
    config_path = base_dir / "geodocs_config.json"
    
    if dev:
        tmp = api_class(config_path)
        tmp.save_config(dev)
        ok, src = try_ping(tmp)
        if ok:
            return "development", dev
            
    if prod:
        tmp = api_class(config_path)
        tmp.save_config(prod)
        ok, src = try_ping(tmp)
        if ok:
            return "production", prod
            
    return None, None