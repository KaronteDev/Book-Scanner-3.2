#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stats_panel.py — Statistics dashboard for Book Scanner projects
Displays comprehensive metrics about scanning progress, OCR completion, and quality
"""
import tkinter as tk
from tkinter import messagebox
try:
    import ttkbootstrap as ttk
    from ttkbootstrap.dialogs import Messagebox
    USE_BOOTSTRAP = True
except ImportError:
    from tkinter import ttk
    Messagebox = None
    USE_BOOTSTRAP = False
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import sqlite3
from utils.window_utils import center_to_parent
from utils import db_manager as db


class StatsPanel:
    """Statistics dashboard window for project metrics"""
    
    def __init__(self, parent, project_db_path: Path):
        self.parent = parent
        self.project_db_path = project_db_path
        self.stats_data = {}
        
        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title("📊 Estadísticas del Proyecto")
        self.window.geometry("900x700")
        
        if parent:
            center_to_parent(self.window, parent)
        
        self._build_ui()
        self._load_stats()
        self._update_display()
        
    def _build_ui(self):
        """Build the statistics UI"""
        main_frame = ttk.Frame(self.window, padding=15)
        main_frame.pack(fill='both', expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="📊 Estadísticas del Proyecto",
            font=("Segoe UI", 16, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Create notebook with tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill='both', expand=True, pady=10)
        
        # Tab 1: General Overview
        self.tab_overview = ttk.Frame(notebook, padding=15)
        notebook.add(self.tab_overview, text="📋 General")
        
        # Tab 2: OCR Statistics
        self.tab_ocr = ttk.Frame(notebook, padding=15)
        notebook.add(self.tab_ocr, text="📝 OCR")
        
        # Tab 3: Quality Statistics
        self.tab_quality = ttk.Frame(notebook, padding=15)
        notebook.add(self.tab_quality, text="⭐ Calidad")
        
        # Tab 4: Timeline
        self.tab_timeline = ttk.Frame(notebook, padding=15)
        notebook.add(self.tab_timeline, text="📅 Cronología")
        
        # Build each tab
        self._build_overview_tab()
        self._build_ocr_tab()
        self._build_quality_tab()
        self._build_timeline_tab()
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)
        
        ttk.Button(
            btn_frame,
            text="🔄 Actualizar",
            command=self.refresh,
            bootstyle="primary" if USE_BOOTSTRAP else None
        ).pack(side='left', padx=5)
        
        ttk.Button(
            btn_frame,
            text="📋 Exportar CSV",
            command=self._export_csv,
            bootstyle="info" if USE_BOOTSTRAP else None
        ).pack(side='left', padx=5)
        
        ttk.Button(
            btn_frame,
            text="Cerrar",
            command=self.window.destroy,
            bootstyle="secondary" if USE_BOOTSTRAP else None
        ).pack(side='left', padx=5)
        
    def _build_overview_tab(self):
        """Build general overview tab"""
        # Stats cards frame
        cards_frame = ttk.Frame(self.tab_overview)
        cards_frame.pack(fill='both', expand=True)
        
        # Create 4 stat cards in 2x2 grid
        self.lbl_total_pages = self._create_stat_card(
            cards_frame, "📄 Total Páginas", "0", 0, 0
        )
        
        self.lbl_total_images = self._create_stat_card(
            cards_frame, "🖼️ Total Imágenes", "0", 0, 1
        )
        
        self.lbl_total_size = self._create_stat_card(
            cards_frame, "💾 Tamaño Total", "0 MB", 1, 0
        )
        
        self.lbl_project_age = self._create_stat_card(
            cards_frame, "📅 Antigüedad", "0 días", 1, 1
        )
        
        # Progress bars section
        progress_frame = ttk.LabelFrame(
            self.tab_overview,
            text="Progreso General",
            padding=15
        )
        progress_frame.pack(fill='x', pady=20)
        
        # OCR Progress
        ttk.Label(progress_frame, text="Progreso OCR:").grid(row=0, column=0, sticky='w', pady=5)
        self.progress_ocr = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            length=400
        )
        self.progress_ocr.grid(row=0, column=1, padx=10, pady=5)
        self.lbl_progress_ocr = ttk.Label(progress_frame, text="0%")
        self.lbl_progress_ocr.grid(row=0, column=2, pady=5)
        
        # Quality Progress
        ttk.Label(progress_frame, text="Calidad Revisada:").grid(row=1, column=0, sticky='w', pady=5)
        self.progress_quality = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            length=400
        )
        self.progress_quality.grid(row=1, column=1, padx=10, pady=5)
        self.lbl_progress_quality = ttk.Label(progress_frame, text="0%")
        self.lbl_progress_quality.grid(row=1, column=2, pady=5)
        
    def _build_ocr_tab(self):
        """Build OCR statistics tab"""
        # OCR status breakdown
        status_frame = ttk.LabelFrame(self.tab_ocr, text="Estado OCR", padding=15)
        status_frame.pack(fill='x', pady=10)
        
        self.lbl_ocr_pending = self._create_label_row(
            status_frame, "⏳ Pendientes:", "0", 0
        )
        self.lbl_ocr_processing = self._create_label_row(
            status_frame, "⚙️ En proceso:", "0", 1
        )
        self.lbl_ocr_completed = self._create_label_row(
            status_frame, "✓ Completados:", "0", 2
        )
        self.lbl_ocr_error = self._create_label_row(
            status_frame, "✗ Con errores:", "0", 3
        )
        
        # OCR quality metrics
        metrics_frame = ttk.LabelFrame(self.tab_ocr, text="Métricas de Texto", padding=15)
        metrics_frame.pack(fill='x', pady=10)
        
        self.lbl_total_chars = self._create_label_row(
            metrics_frame, "Total caracteres:", "0", 0
        )
        self.lbl_total_words = self._create_label_row(
            metrics_frame, "Total palabras:", "0", 1
        )
        self.lbl_avg_confidence = self._create_label_row(
            metrics_frame, "Confianza promedio:", "0%", 2
        )
        
        # Recent OCR activity
        recent_frame = ttk.LabelFrame(self.tab_ocr, text="Actividad Reciente (últimos 7 días)", padding=15)
        recent_frame.pack(fill='both', expand=True, pady=10)
        
        # Treeview for recent OCR
        columns = ("page", "date", "words", "confidence")
        self.tree_recent_ocr = ttk.Treeview(recent_frame, columns=columns, show='headings', height=10)
        
        self.tree_recent_ocr.heading("page", text="Página")
        self.tree_recent_ocr.heading("date", text="Fecha")
        self.tree_recent_ocr.heading("words", text="Palabras")
        self.tree_recent_ocr.heading("confidence", text="Confianza")
        
        self.tree_recent_ocr.column("page", width=150)
        self.tree_recent_ocr.column("date", width=150)
        self.tree_recent_ocr.column("words", width=100)
        self.tree_recent_ocr.column("confidence", width=100)
        
        scrollbar = ttk.Scrollbar(recent_frame, orient="vertical", command=self.tree_recent_ocr.yview)
        self.tree_recent_ocr.configure(yscrollcommand=scrollbar.set)
        
        self.tree_recent_ocr.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
    def _build_quality_tab(self):
        """Build quality statistics tab"""
        # Quality distribution
        dist_frame = ttk.LabelFrame(self.tab_quality, text="Distribución de Calidad", padding=15)
        dist_frame.pack(fill='x', pady=10)
        
        self.lbl_quality_excelente = self._create_label_row(
            dist_frame, "⭐⭐⭐ Excelente:", "0", 0
        )
        self.lbl_quality_buena = self._create_label_row(
            dist_frame, "⭐⭐ Buena:", "0", 1
        )
        self.lbl_quality_regular = self._create_label_row(
            dist_frame, "⭐ Regular:", "0", 2
        )
        self.lbl_quality_mala = self._create_label_row(
            dist_frame, "✗ Mala:", "0", 3
        )
        self.lbl_quality_sin_revisar = self._create_label_row(
            dist_frame, "❓ Sin revisar:", "0", 4
        )
        
        # Average quality score
        avg_frame = ttk.LabelFrame(self.tab_quality, text="Calidad Promedio", padding=15)
        avg_frame.pack(fill='x', pady=10)
        
        self.lbl_avg_quality = ttk.Label(
            avg_frame,
            text="0.0 / 3.0",
            font=("Segoe UI", 24, "bold"),
            foreground="#0066cc"
        )
        self.lbl_avg_quality.pack(pady=10)
        
        # Quality issues
        issues_frame = ttk.LabelFrame(self.tab_quality, text="Problemas Detectados", padding=15)
        issues_frame.pack(fill='both', expand=True, pady=10)
        
        self.lbl_blur_issues = self._create_label_row(
            issues_frame, "🌫️ Desenfoque:", "0", 0
        )
        self.lbl_lighting_issues = self._create_label_row(
            issues_frame, "💡 Iluminación:", "0", 1
        )
        self.lbl_skew_issues = self._create_label_row(
            issues_frame, "📐 Inclinación:", "0", 2
        )
        
    def _build_timeline_tab(self):
        """Build timeline/chronology tab"""
        # Daily activity
        daily_frame = ttk.LabelFrame(self.tab_timeline, text="Actividad Diaria", padding=15)
        daily_frame.pack(fill='both', expand=True, pady=10)
        
        # Treeview for daily stats
        columns = ("date", "pages", "ocr", "time")
        self.tree_daily = ttk.Treeview(daily_frame, columns=columns, show='headings', height=15)
        
        self.tree_daily.heading("date", text="Fecha")
        self.tree_daily.heading("pages", text="Páginas Capturadas")
        self.tree_daily.heading("ocr", text="OCR Completados")
        self.tree_daily.heading("time", text="Tiempo Estimado")
        
        self.tree_daily.column("date", width=150)
        self.tree_daily.column("pages", width=150)
        self.tree_daily.column("ocr", width=150)
        self.tree_daily.column("time", width=150)
        
        scrollbar = ttk.Scrollbar(daily_frame, orient="vertical", command=self.tree_daily.yview)
        self.tree_daily.configure(yscrollcommand=scrollbar.set)
        
        self.tree_daily.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Summary
        summary_frame = ttk.Frame(self.tab_timeline)
        summary_frame.pack(fill='x', pady=10)
        
        self.lbl_most_productive = ttk.Label(
            summary_frame,
            text="Día más productivo: -",
            font=("Segoe UI", 10)
        )
        self.lbl_most_productive.pack(pady=5)
        
    def _create_stat_card(self, parent, title: str, value: str, row: int, col: int):
        """Create a statistics card widget"""
        card = ttk.Frame(parent, relief='ridge', borderwidth=2, padding=15)
        card.grid(row=row, column=col, padx=10, pady=10, sticky='nsew')
        
        ttk.Label(
            card,
            text=title,
            font=("Segoe UI", 10)
        ).pack()
        
        value_label = ttk.Label(
            card,
            text=value,
            font=("Segoe UI", 24, "bold"),
            foreground="#0066cc"
        )
        value_label.pack(pady=10)
        
        parent.columnconfigure(col, weight=1)
        parent.rowconfigure(row, weight=1)
        
        return value_label
        
    def _create_label_row(self, parent, label: str, value: str, row: int):
        """Create a label row with title and value"""
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky='w', pady=5, padx=(0, 20))
        value_label = ttk.Label(parent, text=value, font=("Segoe UI", 10, "bold"))
        value_label.grid(row=row, column=1, sticky='w', pady=5)
        return value_label
        
    def _load_stats(self):
        """Load statistics from database"""
        try:
            conn = sqlite3.connect(self.project_db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            # General stats
            total_pages = cur.execute("SELECT COUNT(*) FROM page").fetchone()[0]
            total_images = cur.execute("SELECT COUNT(*) FROM page WHERE image_path IS NOT NULL").fetchone()[0]
            
            # Calculate total size (estimate)
            total_size_mb = total_images * 2.5  # Rough estimate: 2.5 MB per image
            
            # Project age
            oldest = cur.execute("SELECT MIN(created_at) FROM page").fetchone()[0]
            project_age_days = 0
            if oldest:
                try:
                    created = datetime.fromisoformat(oldest)
                    project_age_days = (datetime.now() - created).days
                except:
                    pass
            
            # OCR stats
            ocr_pending = cur.execute("SELECT COUNT(*) FROM page WHERE ocr_status = 'pending'").fetchone()[0]
            ocr_processing = cur.execute("SELECT COUNT(*) FROM page WHERE ocr_status = 'processing'").fetchone()[0]
            ocr_completed = cur.execute("SELECT COUNT(*) FROM page WHERE ocr_status = 'completed'").fetchone()[0]
            ocr_error = cur.execute("SELECT COUNT(*) FROM page WHERE ocr_status = 'error'").fetchone()[0]
            
            # Text metrics
            result = cur.execute("""
                SELECT 
                    SUM(LENGTH(ocr_corregido)) as total_chars,
                    SUM(LENGTH(ocr_corregido) - LENGTH(REPLACE(ocr_corregido, ' ', '')) + 1) as total_words,
                    AVG(CAST(ocr_confidence as FLOAT)) as avg_confidence
                FROM page 
                WHERE ocr_corregido IS NOT NULL AND ocr_corregido != ''
            """).fetchone()
            
            total_chars = result[0] or 0
            total_words = result[1] or 0
            avg_confidence = result[2] or 0
            
            # Quality stats
            quality_counts = {}
            for level in ['excelente', 'buena', 'regular', 'mala', None]:
                count = cur.execute(
                    "SELECT COUNT(*) FROM page WHERE quality_level = ?",
                    (level,)
                ).fetchone()[0]
                quality_counts[level if level else 'sin_revisar'] = count
            
            # Calculate average quality (1-3 scale)
            quality_map = {'mala': 1, 'regular': 2, 'buena': 2.5, 'excelente': 3}
            total_reviewed = sum(quality_counts.get(k, 0) for k in quality_map.keys())
            if total_reviewed > 0:
                avg_quality = sum(
                    quality_counts.get(k, 0) * v 
                    for k, v in quality_map.items()
                ) / total_reviewed
            else:
                avg_quality = 0
            
            # Recent OCR activity (last 7 days)
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            recent_ocr = cur.execute("""
                SELECT 
                    page_number,
                    ocr_completed_at,
                    LENGTH(ocr_corregido) - LENGTH(REPLACE(ocr_corregido, ' ', '')) + 1 as word_count,
                    ocr_confidence
                FROM page
                WHERE ocr_completed_at > ? AND ocr_status = 'completed'
                ORDER BY ocr_completed_at DESC
                LIMIT 20
            """, (week_ago,)).fetchall()
            
            # Daily activity
            daily_stats = cur.execute("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as pages_count,
                    SUM(CASE WHEN ocr_status = 'completed' THEN 1 ELSE 0 END) as ocr_count
                FROM page
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                LIMIT 30
            """).fetchall()
            
            conn.close()
            
            # Store in stats_data
            self.stats_data = {
                'total_pages': total_pages,
                'total_images': total_images,
                'total_size_mb': total_size_mb,
                'project_age_days': project_age_days,
                'ocr_pending': ocr_pending,
                'ocr_processing': ocr_processing,
                'ocr_completed': ocr_completed,
                'ocr_error': ocr_error,
                'total_chars': total_chars,
                'total_words': total_words,
                'avg_confidence': avg_confidence,
                'quality_counts': quality_counts,
                'avg_quality': avg_quality,
                'recent_ocr': recent_ocr,
                'daily_stats': daily_stats
            }
            
        except Exception as e:
            print(f"Error loading stats: {e}")
            self.stats_data = {}
            
    def _update_display(self):
        """Update UI with loaded stats"""
        if not self.stats_data:
            return
            
        # Overview tab
        self.lbl_total_pages.config(text=str(self.stats_data.get('total_pages', 0)))
        self.lbl_total_images.config(text=str(self.stats_data.get('total_images', 0)))
        self.lbl_total_size.config(text=f"{self.stats_data.get('total_size_mb', 0):.1f} MB")
        self.lbl_project_age.config(text=f"{self.stats_data.get('project_age_days', 0)} días")
        
        # Progress bars
        total = self.stats_data.get('total_pages', 1)
        ocr_done = self.stats_data.get('ocr_completed', 0)
        ocr_percent = (ocr_done / total * 100) if total > 0 else 0
        self.progress_ocr['value'] = ocr_percent
        self.lbl_progress_ocr.config(text=f"{ocr_percent:.1f}%")
        
        quality_reviewed = total - self.stats_data.get('quality_counts', {}).get('sin_revisar', total)
        quality_percent = (quality_reviewed / total * 100) if total > 0 else 0
        self.progress_quality['value'] = quality_percent
        self.lbl_progress_quality.config(text=f"{quality_percent:.1f}%")
        
        # OCR tab
        self.lbl_ocr_pending.config(text=str(self.stats_data.get('ocr_pending', 0)))
        self.lbl_ocr_processing.config(text=str(self.stats_data.get('ocr_processing', 0)))
        self.lbl_ocr_completed.config(text=str(self.stats_data.get('ocr_completed', 0)))
        self.lbl_ocr_error.config(text=str(self.stats_data.get('ocr_error', 0)))
        
        self.lbl_total_chars.config(text=f"{self.stats_data.get('total_chars', 0):,}")
        self.lbl_total_words.config(text=f"{self.stats_data.get('total_words', 0):,}")
        self.lbl_avg_confidence.config(text=f"{self.stats_data.get('avg_confidence', 0):.1f}%")
        
        # Recent OCR
        self.tree_recent_ocr.delete(*self.tree_recent_ocr.get_children())
        for row in self.stats_data.get('recent_ocr', []):
            date_str = row[1][:10] if row[1] else "-"
            self.tree_recent_ocr.insert("", "end", values=(
                f"Pág. {row[0]}",
                date_str,
                row[2] or 0,
                f"{row[3] or 0:.1f}%"
            ))
        
        # Quality tab
        qc = self.stats_data.get('quality_counts', {})
        self.lbl_quality_excelente.config(text=str(qc.get('excelente', 0)))
        self.lbl_quality_buena.config(text=str(qc.get('buena', 0)))
        self.lbl_quality_regular.config(text=str(qc.get('regular', 0)))
        self.lbl_quality_mala.config(text=str(qc.get('mala', 0)))
        self.lbl_quality_sin_revisar.config(text=str(qc.get('sin_revisar', 0)))
        
        avg_q = self.stats_data.get('avg_quality', 0)
        self.lbl_avg_quality.config(text=f"{avg_q:.2f} / 3.0")
        
        # Timeline tab
        self.tree_daily.delete(*self.tree_daily.get_children())
        most_productive_day = None
        max_pages = 0
        
        for row in self.stats_data.get('daily_stats', []):
            date_str = row[0]
            pages_count = row[1]
            ocr_count = row[2]
            est_time = f"{pages_count * 2} min"  # Estimate 2 min per page
            
            self.tree_daily.insert("", "end", values=(
                date_str,
                pages_count,
                ocr_count,
                est_time
            ))
            
            if pages_count > max_pages:
                max_pages = pages_count
                most_productive_day = date_str
        
        if most_productive_day:
            self.lbl_most_productive.config(
                text=f"Día más productivo: {most_productive_day} ({max_pages} páginas)"
            )
    
    def refresh(self):
        """Refresh statistics"""
        self._load_stats()
        self._update_display()
        
    def _export_csv(self):
        """Export statistics to CSV file"""
        from tkinter import filedialog
        import csv
        
        filepath = filedialog.asksaveasfilename(
            parent=self.window,
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="estadisticas_proyecto.csv"
        )
        
        if not filepath:
            return
            
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # General stats
                writer.writerow(["ESTADÍSTICAS GENERALES"])
                writer.writerow(["Total Páginas", self.stats_data.get('total_pages', 0)])
                writer.writerow(["Total Imágenes", self.stats_data.get('total_images', 0)])
                writer.writerow(["Tamaño Total (MB)", f"{self.stats_data.get('total_size_mb', 0):.1f}"])
                writer.writerow(["Antigüedad (días)", self.stats_data.get('project_age_days', 0)])
                writer.writerow([])
                
                # OCR stats
                writer.writerow(["ESTADÍSTICAS OCR"])
                writer.writerow(["Pendientes", self.stats_data.get('ocr_pending', 0)])
                writer.writerow(["En Proceso", self.stats_data.get('ocr_processing', 0)])
                writer.writerow(["Completados", self.stats_data.get('ocr_completed', 0)])
                writer.writerow(["Errores", self.stats_data.get('ocr_error', 0)])
                writer.writerow([])
                
                # Quality stats
                writer.writerow(["ESTADÍSTICAS DE CALIDAD"])
                qc = self.stats_data.get('quality_counts', {})
                writer.writerow(["Excelente", qc.get('excelente', 0)])
                writer.writerow(["Buena", qc.get('buena', 0)])
                writer.writerow(["Regular", qc.get('regular', 0)])
                writer.writerow(["Mala", qc.get('mala', 0)])
                writer.writerow(["Sin Revisar", qc.get('sin_revisar', 0)])
                
            if Messagebox:
                Messagebox.show_info(
                    title="Exportación Exitosa",
                    message=f"Estadísticas exportadas a:\n{filepath}",
                    parent=self.window
                )
            else:
                messagebox.showinfo(
                    "Exportación Exitosa",
                    f"Estadísticas exportadas a:\n{filepath}",
                    parent=self.window
                )
                
        except Exception as e:
            if Messagebox:
                Messagebox.show_error(
                    title="Error",
                    message=f"Error al exportar: {e}",
                    parent=self.window
                )
            else:
                messagebox.showerror("Error", f"Error al exportar: {e}", parent=self.window)


def show_stats_panel(parent, project_db_path: Path):
    """Show statistics panel window"""
    panel = StatsPanel(parent, project_db_path)
    return panel
