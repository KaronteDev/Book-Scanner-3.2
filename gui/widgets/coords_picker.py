#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reusable coordinates picker dialog that opens an interactive Leaflet map
in the system browser and receives the selected coordinates back via
utils.map_browser (local HTTP callback).

Usage:
    lat_lon = open_coords_picker(parent, initial_lat=40.4168, initial_lon=-3.7038)
    if lat_lon: lat, lon = lat_lon
"""
import tkinter as tk
from tkinter import messagebox
from typing import Optional, Tuple

try:
    from utils.map_browser import abrir_mapa_navegador
except Exception:
    abrir_mapa_navegador = None


class CoordsPickerDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, initial_lat: float = 40.4168, initial_lon: float = -3.7038):
        super().__init__(parent)
        self.title("Elegir coordenadas")
        self.geometry("420x180")
        self.resizable(False, False)
        self.result: Optional[Tuple[float, float]] = None

        frm = tk.Frame(self, padx=12, pady=12)
        frm.pack(fill=tk.BOTH, expand=True)

        tk.Label(frm, text="Latitud:").grid(row=0, column=0, sticky="e", padx=6, pady=6)
        tk.Label(frm, text="Longitud:").grid(row=1, column=0, sticky="e", padx=6, pady=6)

        self.var_lat = tk.StringVar(value=f"{initial_lat:.6f}")
        self.var_lon = tk.StringVar(value=f"{initial_lon:.6f}")

        e1 = tk.Entry(frm, textvariable=self.var_lat, width=18)
        e2 = tk.Entry(frm, textvariable=self.var_lon, width=18)
        e1.grid(row=0, column=1, sticky="w"); e2.grid(row=1, column=1, sticky="w")

        btns = tk.Frame(frm)
        btns.grid(row=2, column=0, columnspan=2, sticky="we", pady=(10,0))

        tk.Button(btns, text="Mapa interactivo (Navegador)", command=self._open_map).pack(side=tk.LEFT)
        tk.Button(btns, text="Aceptar", command=self._accept).pack(side=tk.RIGHT, padx=6)
        tk.Button(btns, text="Cancelar", command=self.destroy).pack(side=tk.RIGHT)

        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _open_map(self):
        if abrir_mapa_navegador is None:
            messagebox.showerror("Mapa", "Función de navegador no disponible.")
            return
        # Parse current numbers if possible
        def _parse(v: str, default: float) -> float:
            try:
                return float(v)
            except Exception:
                return default
        lat0 = _parse(self.var_lat.get(), 40.4168)
        lon0 = _parse(self.var_lon.get(), -3.7038)
        try:
            coords = abrir_mapa_navegador(lat0, lon0, True, puerto=8765, timeout=180)
        except Exception as ex:
            messagebox.showerror("Mapa", f"Error abriendo mapa: {ex}")
            return
        if coords:
            try:
                lat_s, lon_s = [s.strip() for s in coords.split(",", 1)]
                lat_v = float(lat_s); lon_v = float(lon_s)
                self.var_lat.set(f"{lat_v:.6f}")
                self.var_lon.set(f"{lon_v:.6f}")
            except Exception:
                messagebox.showwarning("Mapa", f"Coordenadas inválidas recibidas: {coords}")

    def _accept(self):
        try:
            lat = float(self.var_lat.get().strip())
            lon = float(self.var_lon.get().strip())
            self.result = (lat, lon)
            self.destroy()
        except Exception:
            messagebox.showwarning("Coordenadas", "Valores no válidos. Use formato decimal.")


def open_coords_picker(parent: tk.Misc, initial_lat: float = 40.4168, initial_lon: float = -3.7038) -> Optional[Tuple[float, float]]:
    dlg = CoordsPickerDialog(parent, initial_lat=initial_lat, initial_lon=initial_lon)
    parent.wait_window(dlg)
    return dlg.result
