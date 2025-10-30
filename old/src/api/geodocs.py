#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import requests
from pathlib import Path

class GeoDocsAPI:
    def __init__(self, config_path: Path, map_path: Path):
        self.config_path = config_path
        self.map_path = map_path
        self.config = self.load_config()
        self.map = self.load_map()
    
    def load_config(self):
        if self.config_path.exists():
            return json.loads(self.config_path.read_text(encoding="utf-8"))
        d = {
            "api_base_url": "",
            "api_key": "",
            "verify_tls": True,
            "timeout_sec": 20
        }
        self.config_path.write_text(json.dumps(d, indent=2), encoding="utf-8")
        return d
    
    def save_config(self, cfg):
        self.config = cfg
        self.config_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    
    def load_map(self):
        if self.map_path.exists():
            return json.loads(self.map_path.read_text(encoding="utf-8"))
        m = {
            "endpoints": {},
            "field_map": {
                "document": {},
                "page": {}
            }
        }
        self.map_path.write_text(json.dumps(m, indent=2), encoding="utf-8")
        return m
    
    def save_map(self, m):
        self.map = m
        self.map_path.write_text(json.dumps(m, indent=2), encoding="utf-8")
    
    def headers(self):
        h = {"Content-Type": "application/json"}
        if (self.config.get("auth") or "").lower() == "jwt":
            tok = self.config.get("jwt_token") or ""
            if tok:
                h["Authorization"] = f"Bearer {tok}"
        else:
            key = self.config.get("api_key") or ""
            if key:
                h["Authorization"] = f"Bearer {key}"
        return h
    
    def base(self):
        return (self.config.get("api_base_url") or "").rstrip("/")
    
    def timeout(self):
        return int(self.config.get("timeout_sec", 20))
    
    def verify(self):
        return bool(self.config.get("verify_tls", True))
    
    def get(self, path, params=None):
        url = f"{self.base()}{path}"
        r = requests.get(url, headers=self.headers(),
                        params=params or {},
                        timeout=self.timeout(),
                        verify=self.verify())
        r.raise_for_status()
        return r.json()
    
    def post(self, path, payload):
        url = f"{self.base()}{path}"
        r = requests.post(url, headers=self.headers(),
                         json=payload,
                         timeout=self.timeout(),
                         verify=self.verify())
        r.raise_for_status()
        return r.json()
    
    def map_local_to_remote_doc(self, doc: dict):
        fmap = self.map.get("field_map", {}).get("document", {})
        return {remote: doc.get(local) for local, remote in fmap.items()}
    
    def map_local_to_remote_page(self, page: dict):
        fmap = self.map.get("field_map", {}).get("page", {})
        return {remote: page.get(local) for local, remote in fmap.items()}
    
    def map_remote_to_local_doc(self, remote: dict):
        fmap = self.map.get("field_map", {}).get("document", {})
        inv = {v: k for k, v in fmap.items()}
        return {inv[rk]: rv for rk, rv in remote.items() if rk in inv}
    
    def map_remote_to_local_page(self, remote: dict):
        fmap = self.map.get("field_map", {}).get("page", {})
        inv = {v: k for k, v in fmap.items()}
        return {inv[rk]: rv for rk, rv in remote.items() if rk in inv}
    
    def search_toponimos(self, q):
        ep = "/api/toponimos"
        return self.get(ep, params={"search": q})
    
    def search_personas(self, q):
        ep = "/api/personas" 
        return self.get(ep, params={"search": q})
    
    def push_document(self, doc_id, db):
        from ..database.db import Database
        
        # Obtener documento y páginas
        doc = db.get_document(doc_id)
        pages = db.get_pages(doc_id)
        
        # Mapear a esquema remoto
        doc_remote = self.map_local_to_remote_doc(dict(doc))
        pages_remote = [self.map_local_to_remote_page(dict(p)) for p in pages]
        
        # Enviar
        payload = {"document": doc_remote, "pages": pages_remote}
        ep = self.map.get("endpoints", {}).get("push_document", "/api/sync/document")
        return self.post(ep, payload)