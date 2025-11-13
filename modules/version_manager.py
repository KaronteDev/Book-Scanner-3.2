#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
version_manager.py — Gestión de historial de versiones para OCR y anotaciones
"""
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import sqlite3
import json
from datetime import datetime


class VersionManager:
    """
    Gestor de versiones para OCR, anotaciones y metadatos.
    Permite crear snapshots, revertir cambios y comparar versiones.
    """
    
    def __init__(self, project_db_path: Path):
        """
        Args:
            project_db_path: Ruta a project.db
        """
        self.project_db = project_db_path
    
    def _connect(self) -> sqlite3.Connection:
        """Crear conexión a la BD"""
        conn = sqlite3.connect(self.project_db)
        conn.row_factory = sqlite3.Row
        return conn
    
    def create_version(
        self,
        entity_type: str,
        entity_id: int,
        data: Dict[str, Any],
        user_notes: str = ""
    ) -> int:
        """
        Crear una nueva versión (snapshot).
        
        Args:
            entity_type: Tipo de entidad ('ocr', 'annotation', 'metadata')
            entity_id: ID de la entidad (page_id, annotation_id, etc.)
            data: Datos a versionar (se guarda como JSON)
            user_notes: Notas del usuario sobre el cambio
        
        Returns:
            Número de versión creada
        """
        with self._connect() as conn:
            cursor = conn.cursor()
            
            # Obtener siguiente número de versión
            cursor.execute("""
                SELECT COALESCE(MAX(version), 0) + 1
                FROM versions
                WHERE entity_type = ? AND entity_id = ?
            """, (entity_type, entity_id))
            next_version = cursor.fetchone()[0]
            
            # Insertar nueva versión
            data_json = json.dumps(data, ensure_ascii=False)
            cursor.execute("""
                INSERT INTO versions (entity_type, entity_id, version, data_json, user_notes)
                VALUES (?, ?, ?, ?, ?)
            """, (entity_type, entity_id, next_version, data_json, user_notes))
            
            # Actualizar current_version si es OCR
            if entity_type == 'ocr':
                cursor.execute("""
                    UPDATE page
                    SET current_ocr_version = ?
                    WHERE id = ?
                """, (next_version, entity_id))
            
            conn.commit()
            return next_version
    
    def get_version(
        self,
        entity_type: str,
        entity_id: int,
        version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Obtener una versión específica.
        
        Args:
            entity_type: Tipo de entidad
            entity_id: ID de la entidad
            version: Número de versión (None = última)
        
        Returns:
            Dict con los datos de la versión o None
        """
        with self._connect() as conn:
            cursor = conn.cursor()
            
            if version is None:
                # Obtener última versión
                cursor.execute("""
                    SELECT version, data_json, user_notes, created_at
                    FROM versions
                    WHERE entity_type = ? AND entity_id = ?
                    ORDER BY version DESC
                    LIMIT 1
                """, (entity_type, entity_id))
            else:
                cursor.execute("""
                    SELECT version, data_json, user_notes, created_at
                    FROM versions
                    WHERE entity_type = ? AND entity_id = ? AND version = ?
                """, (entity_type, entity_id, version))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return {
                'version': row['version'],
                'data': json.loads(row['data_json']),
                'user_notes': row['user_notes'],
                'created_at': row['created_at']
            }
    
    def list_versions(
        self,
        entity_type: str,
        entity_id: int
    ) -> List[Dict[str, Any]]:
        """
        Listar todas las versiones de una entidad.
        
        Returns:
            Lista de dicts con info de cada versión (sin data completa)
        """
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT version, user_notes, created_at,
                       LENGTH(data_json) as data_size
                FROM versions
                WHERE entity_type = ? AND entity_id = ?
                ORDER BY version DESC
            """, (entity_type, entity_id))
            
            return [
                {
                    'version': row['version'],
                    'user_notes': row['user_notes'],
                    'created_at': row['created_at'],
                    'data_size': row['data_size']
                }
                for row in cursor.fetchall()
            ]
    
    def revert_to_version(
        self,
        entity_type: str,
        entity_id: int,
        target_version: int,
        create_snapshot: bool = True
    ) -> bool:
        """
        Revertir a una versión anterior.
        
        Args:
            entity_type: Tipo de entidad
            entity_id: ID de la entidad
            target_version: Versión a la que revertir
            create_snapshot: Si crear snapshot antes de revertir
        
        Returns:
            True si se revirtió correctamente
        """
        # Obtener datos de la versión target
        version_data = self.get_version(entity_type, entity_id, target_version)
        if not version_data:
            return False
        
        data = version_data['data']
        
        # Crear snapshot del estado actual antes de revertir
        if create_snapshot:
            current = self.get_current_data(entity_type, entity_id)
            if current:
                self.create_version(
                    entity_type,
                    entity_id,
                    current,
                    user_notes=f"Snapshot automático antes de revertir a v{target_version}"
                )
        
        # Aplicar datos de la versión anterior
        with self._connect() as conn:
            cursor = conn.cursor()
            
            if entity_type == 'ocr':
                # Actualizar texto OCR en page
                cursor.execute("""
                    UPDATE page
                    SET ocr_original = ?, ocr_corregido = ?
                    WHERE id = ?
                """, (
                    data.get('ocr_original', ''),
                    data.get('ocr_corregido', ''),
                    entity_id
                ))
            elif entity_type == 'annotation':
                # Actualizar anotación
                cursor.execute("""
                    UPDATE annotation
                    SET text = ?, data = ?
                    WHERE id = ?
                """, (
                    data.get('text', ''),
                    json.dumps(data.get('extra_data', {})),
                    entity_id
                ))
            # TODO: Añadir más tipos según necesidad
            
            conn.commit()
        
        return True
    
    def get_current_data(
        self,
        entity_type: str,
        entity_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Obtener datos actuales de una entidad para crear snapshot.
        
        Returns:
            Dict con datos actuales o None
        """
        with self._connect() as conn:
            cursor = conn.cursor()
            
            if entity_type == 'ocr':
                cursor.execute("""
                    SELECT ocr_original, ocr_corregido, status
                    FROM page
                    WHERE id = ?
                """, (entity_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        'ocr_original': row['ocr_original'] or '',
                        'ocr_corregido': row['ocr_corregido'] or '',
                        'status': row['status']
                    }
            elif entity_type == 'annotation':
                cursor.execute("""
                    SELECT text, data
                    FROM annotation
                    WHERE id = ?
                """, (entity_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        'text': row['text'],
                        'extra_data': json.loads(row['data'] or '{}')
                    }
        
        return None
    
    def compare_versions(
        self,
        entity_type: str,
        entity_id: int,
        version_a: int,
        version_b: int
    ) -> Dict[str, Any]:
        """
        Comparar dos versiones.
        
        Returns:
            Dict con información de diferencias
        """
        data_a = self.get_version(entity_type, entity_id, version_a)
        data_b = self.get_version(entity_type, entity_id, version_b)
        
        if not data_a or not data_b:
            return {'error': 'Versión no encontrada'}
        
        # Comparación simple de claves
        diff = {
            'version_a': version_a,
            'version_b': version_b,
            'changes': []
        }
        
        for key in set(list(data_a['data'].keys()) + list(data_b['data'].keys())):
            val_a = data_a['data'].get(key)
            val_b = data_b['data'].get(key)
            
            if val_a != val_b:
                diff['changes'].append({
                    'field': key,
                    'old_value': val_a,
                    'new_value': val_b
                })
        
        return diff
    
    def delete_old_versions(
        self,
        entity_type: str,
        entity_id: int,
        keep_last_n: int = 10
    ) -> int:
        """
        Eliminar versiones antiguas para liberar espacio.
        
        Args:
            keep_last_n: Número de versiones recientes a mantener
        
        Returns:
            Número de versiones eliminadas
        """
        with self._connect() as conn:
            cursor = conn.cursor()
            
            # Obtener versiones a eliminar
            cursor.execute("""
                SELECT version
                FROM versions
                WHERE entity_type = ? AND entity_id = ?
                ORDER BY version DESC
                LIMIT -1 OFFSET ?
            """, (entity_type, entity_id, keep_last_n))
            
            versions_to_delete = [row['version'] for row in cursor.fetchall()]
            
            if not versions_to_delete:
                return 0
            
            # Eliminar
            placeholders = ','.join('?' * len(versions_to_delete))
            cursor.execute(f"""
                DELETE FROM versions
                WHERE entity_type = ? AND entity_id = ? AND version IN ({placeholders})
            """, [entity_type, entity_id] + versions_to_delete)
            
            conn.commit()
            return len(versions_to_delete)
    
    def get_version_stats(self) -> Dict[str, int]:
        """
        Obtener estadísticas del sistema de versiones.
        
        Returns:
            Dict con contadores
        """
        with self._connect() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    entity_type,
                    COUNT(*) as count,
                    SUM(LENGTH(data_json)) as total_size
                FROM versions
                GROUP BY entity_type
            """)
            
            stats = {}
            for row in cursor.fetchall():
                stats[row['entity_type']] = {
                    'count': row['count'],
                    'total_size_bytes': row['total_size'] or 0
                }
            
            return stats
