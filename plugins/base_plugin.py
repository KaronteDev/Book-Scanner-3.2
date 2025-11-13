#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
base_plugin.py — Clase base abstracta para plugins
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path


class BasePlugin(ABC):
    """
    Clase base para todos los plugins del Book Scanner.
    
    Todos los plugins deben heredar de esta clase e implementar los métodos abstractos.
    """
    
    def __init__(self):
        self.enabled = True
        self.config = {}
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre del plugin"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Versión del plugin (formato: x.y.z)"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Descripción breve del plugin"""
        pass
    
    @property
    def author(self) -> str:
        """Autor del plugin"""
        return "Unknown"
    
    @property
    def requires(self) -> list:
        """Lista de dependencias Python requeridas"""
        return []
    
    def initialize(self, app_context: Dict[str, Any]) -> bool:
        """
        Inicializar el plugin.
        
        Args:
            app_context: Contexto de la aplicación con referencias útiles
                - 'root': tkinter root window
                - 'base_path': Path al directorio raíz de trabajo
                - 'app_config': utilidades de configuración
        
        Returns:
            True si la inicialización fue exitosa
        """
        return True
    
    def shutdown(self) -> None:
        """
        Limpiar recursos antes de cerrar el plugin.
        """
        pass
    
    def get_menu_items(self) -> list:
        """
        Retornar items de menú para integrar en la UI.
        
        Returns:
            Lista de dicts con estructura:
            [
                {
                    'label': 'Mi Acción',
                    'command': self.my_action,
                    'icon': '🔧',  # opcional
                    'accelerator': 'Ctrl+M'  # opcional
                }
            ]
        """
        return []
    
    def get_toolbar_buttons(self) -> list:
        """
        Retornar botones para integrar en la toolbar.
        
        Returns:
            Lista de dicts con estructura:
            [
                {
                    'text': 'Mi Botón',
                    'command': self.my_action,
                    'tooltip': 'Descripción',  # opcional
                }
            ]
        """
        return []
    
    def process_image(self, image_path: Path) -> Optional[Path]:
        """
        Procesar una imagen.
        
        Args:
            image_path: Ruta a la imagen a procesar
        
        Returns:
            Ruta a la imagen procesada (puede ser la misma si se modificó in-place)
            o None si no se procesó
        """
        return None
    
    def process_ocr_text(self, text: str, metadata: Dict[str, Any] = None) -> str:
        """
        Procesar texto OCR.
        
        Args:
            text: Texto original
            metadata: Metadatos adicionales (página, proyecto, etc.)
        
        Returns:
            Texto procesado
        """
        return text
    
    def get_settings_panel(self, parent):
        """
        Retornar un widget de configuración para el plugin.
        
        Args:
            parent: Widget padre de tkinter
        
        Returns:
            Widget de tkinter con controles de configuración
            o None si no hay configuración
        """
        return None
    
    def load_config(self, config: Dict[str, Any]) -> None:
        """
        Cargar configuración del plugin.
        
        Args:
            config: Diccionario con configuración
        """
        self.config = config or {}
    
    def save_config(self) -> Dict[str, Any]:
        """
        Guardar configuración del plugin.
        
        Returns:
            Diccionario con configuración
        """
        return self.config
    
    def on_project_opened(self, project_path: Path) -> None:
        """
        Hook llamado cuando se abre un proyecto.
        
        Args:
            project_path: Ruta del proyecto abierto
        """
        pass
    
    def on_project_closed(self) -> None:
        """
        Hook llamado cuando se cierra un proyecto.
        """
        pass
    
    def on_page_captured(self, page_path: Path, metadata: Dict[str, Any]) -> None:
        """
        Hook llamado cuando se captura una página.
        
        Args:
            page_path: Ruta de la página capturada
            metadata: Metadatos de la página
        """
        pass
    
    def on_ocr_completed(self, page_id: int, text: str) -> None:
        """
        Hook llamado cuando se completa el OCR de una página.
        
        Args:
            page_id: ID de la página
            text: Texto OCR extraído
        """
        pass
