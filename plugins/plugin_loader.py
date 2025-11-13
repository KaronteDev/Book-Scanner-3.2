#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plugin_loader.py — Cargador dinámico de plugins
"""
import importlib
import importlib.util
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import logging

from .base_plugin import BasePlugin


logger = logging.getLogger(__name__)


class PluginLoader:
    """
    Gestor de carga y ejecución de plugins.
    """
    
    def __init__(self, plugins_dir: Path, config_path: Optional[Path] = None):
        """
        Args:
            plugins_dir: Directorio donde buscar plugins
            config_path: Archivo JSON con configuración de plugins
        """
        self.plugins_dir = plugins_dir
        self.config_path = config_path or (plugins_dir / "plugins_config.json")
        self.plugins: Dict[str, BasePlugin] = {}
        self.plugin_configs = {}
        
        # Cargar configuración
        self._load_plugin_configs()
    
    def _load_plugin_configs(self):
        """Cargar configuración de plugins desde JSON"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.plugin_configs = json.load(f)
            except Exception as e:
                logger.error(f"Error cargando configuración de plugins: {e}")
                self.plugin_configs = {}
        else:
            self.plugin_configs = {}
    
    def _save_plugin_configs(self):
        """Guardar configuración de plugins a JSON"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.plugin_configs, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error guardando configuración de plugins: {e}")
    
    def discover_plugins(self) -> List[str]:
        """
        Descubrir plugins disponibles en el directorio.
        
        Returns:
            Lista de nombres de módulos de plugins encontrados
        """
        if not self.plugins_dir.exists():
            return []
        
        discovered = []
        
        # Buscar archivos .py que no sean __init__ o base_plugin
        for plugin_file in self.plugins_dir.glob("*.py"):
            if plugin_file.stem in ('__init__', 'base_plugin', 'plugin_loader'):
                continue
            discovered.append(plugin_file.stem)
        
        # Buscar subdirectorios con __init__.py
        for plugin_dir in self.plugins_dir.iterdir():
            if plugin_dir.is_dir() and (plugin_dir / "__init__.py").exists():
                discovered.append(plugin_dir.name)
        
        return discovered
    
    def load_plugin(self, plugin_name: str, app_context: Dict[str, Any]) -> Optional[BasePlugin]:
        """
        Cargar un plugin específico.
        
        Args:
            plugin_name: Nombre del módulo del plugin
            app_context: Contexto de la aplicación
        
        Returns:
            Instancia del plugin o None si falló
        """
        try:
            # Construir ruta del módulo
            module_path = self.plugins_dir / f"{plugin_name}.py"
            
            # Si es un directorio, buscar __init__.py
            if not module_path.exists():
                module_path = self.plugins_dir / plugin_name / "__init__.py"
            
            if not module_path.exists():
                logger.error(f"Plugin no encontrado: {plugin_name}")
                return None
            
            # Cargar el módulo dinámicamente
            spec = importlib.util.spec_from_file_location(f"plugins.{plugin_name}", module_path)
            if spec is None or spec.loader is None:
                logger.error(f"No se pudo crear spec para {plugin_name}")
                return None
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"plugins.{plugin_name}"] = module
            spec.loader.exec_module(module)
            
            # Buscar clase que herede de BasePlugin
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, BasePlugin) and 
                    attr is not BasePlugin):
                    plugin_class = attr
                    break
            
            if plugin_class is None:
                logger.error(f"No se encontró clase BasePlugin en {plugin_name}")
                return None
            
            # Instanciar plugin
            plugin = plugin_class()
            
            # Cargar configuración específica del plugin
            if plugin.name in self.plugin_configs:
                plugin.load_config(self.plugin_configs[plugin.name])
            
            # Inicializar plugin
            if not plugin.initialize(app_context):
                logger.error(f"Falló inicialización de {plugin.name}")
                return None
            
            # Guardar referencia
            self.plugins[plugin.name] = plugin
            
            logger.info(f"Plugin cargado: {plugin.name} v{plugin.version}")
            return plugin
            
        except Exception as e:
            logger.error(f"Error cargando plugin {plugin_name}: {e}", exc_info=True)
            return None
    
    def load_all_plugins(self, app_context: Dict[str, Any]) -> int:
        """
        Cargar todos los plugins descubiertos.
        
        Args:
            app_context: Contexto de la aplicación
        
        Returns:
            Número de plugins cargados exitosamente
        """
        discovered = self.discover_plugins()
        loaded_count = 0
        
        for plugin_name in discovered:
            # Verificar si está habilitado en configuración
            config = self.plugin_configs.get(plugin_name, {})
            if not config.get('enabled', True):
                logger.info(f"Plugin deshabilitado: {plugin_name}")
                continue
            
            plugin = self.load_plugin(plugin_name, app_context)
            if plugin:
                loaded_count += 1
        
        return loaded_count
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Descargar un plugin.
        
        Args:
            plugin_name: Nombre del plugin
        
        Returns:
            True si se descargó correctamente
        """
        if plugin_name not in self.plugins:
            return False
        
        try:
            plugin = self.plugins[plugin_name]
            
            # Guardar configuración
            self.plugin_configs[plugin.name] = plugin.save_config()
            self._save_plugin_configs()
            
            # Llamar shutdown
            plugin.shutdown()
            
            # Eliminar referencia
            del self.plugins[plugin_name]
            
            # Eliminar módulo de sys.modules
            module_name = f"plugins.{plugin_name}"
            if module_name in sys.modules:
                del sys.modules[module_name]
            
            logger.info(f"Plugin descargado: {plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error descargando plugin {plugin_name}: {e}")
            return False
    
    def unload_all_plugins(self):
        """Descargar todos los plugins."""
        plugin_names = list(self.plugins.keys())
        for name in plugin_names:
            self.unload_plugin(name)
    
    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        """
        Obtener un plugin por nombre.
        
        Args:
            name: Nombre del plugin
        
        Returns:
            Instancia del plugin o None
        """
        return self.plugins.get(name)
    
    def get_all_plugins(self) -> Dict[str, BasePlugin]:
        """
        Obtener todos los plugins cargados.
        
        Returns:
            Diccionario {nombre: plugin}
        """
        return self.plugins.copy()
    
    def call_hook(self, hook_name: str, *args, **kwargs):
        """
        Llamar un hook en todos los plugins.
        
        Args:
            hook_name: Nombre del método hook
            *args, **kwargs: Argumentos para el hook
        """
        for plugin in self.plugins.values():
            if not plugin.enabled:
                continue
            
            try:
                method = getattr(plugin, hook_name, None)
                if method and callable(method):
                    method(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error en hook {hook_name} de {plugin.name}: {e}")
    
    def enable_plugin(self, plugin_name: str):
        """Habilitar un plugin."""
        if plugin_name in self.plugins:
            self.plugins[plugin_name].enabled = True
            self.plugin_configs[plugin_name] = self.plugin_configs.get(plugin_name, {})
            self.plugin_configs[plugin_name]['enabled'] = True
            self._save_plugin_configs()
    
    def disable_plugin(self, plugin_name: str):
        """Deshabilitar un plugin."""
        if plugin_name in self.plugins:
            self.plugins[plugin_name].enabled = False
            self.plugin_configs[plugin_name] = self.plugin_configs.get(plugin_name, {})
            self.plugin_configs[plugin_name]['enabled'] = False
            self._save_plugin_configs()
