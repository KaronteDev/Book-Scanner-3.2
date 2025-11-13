#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plugins/__init__.py — Sistema de plugins para Book Scanner
"""
from .plugin_loader import PluginLoader, BasePlugin

__all__ = ['PluginLoader', 'BasePlugin']
