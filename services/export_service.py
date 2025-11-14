from pathlib import Path
from typing import Any, Dict
import json, hashlib
from lxml import etree
from services.exporters.pdf_exporter import export_pdf
from services.exporters.iiif_exporter import export_iiif_manifest
from services.exporters.tei_exporter import export_tei
from services.exporters.dc_exporter import export_dublin_core
from services.exporters.geojson_exporter import export_geojson_annotations

class ExportService:
    """Servicio de exportación.

    Meta unifica distintos formatos (PDF, IIIF, TEI, DC, GeoJSON). Esta clase actuará como
    fachada simplificada que delega en exportadores específicos (patrón Strategy/Façade):

    Métodos previstos:
    - `export_pdf(book, path)`
    - `export_iiif(book, path)`
    - `export_tei(book, path)`
    - `export_bundle(book, dir)` (genera paquete ZIP con todos los formatos)
    - Validación previa y post (estructura mínima, checksums, metadatos).
    """

    def export_book(self, book: Any, destination: str) -> None:
        """Stub genérico: escribe un resumen mínimo en destino.

        Para pruebas iniciales y smoke-tests de la interfaz. Formatos reales se añadirán
        integrando módulos existentes de export y validación.
        """
        try:
            p = Path(destination)
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, 'w', encoding='utf-8') as f:
                f.write(f"Book export stub: {getattr(book, 'title', 'Sin título')}\n")
                f.write(f"Pages: {len(getattr(book, 'pages', []))}\n")
                f.write("Annotations: \n")
                for a in getattr(book, 'annotations', []):
                    f.write(f" - {a.id} page {a.page} text={a.text[:30]}\n")
        except Exception:
            # En implementación real: loggear error
            return

    def export_pdf(self, book: Any, path: str) -> str:
        out = export_pdf(book, path)
        self._validate_output(out, 'pdf')
        return out

    def export_iiif(self, book: Any, path: str) -> str:
        out = export_iiif_manifest(book, path)
        self._validate_output(out, 'iiif')
        return out

    def export_tei(self, book: Any, path: str) -> str:
        out = export_tei(book, path)
        self._validate_output(out, 'tei')
        return out

    def export_dublin_core(self, book: Any, path: str) -> str:
        out = export_dublin_core(book, path)
        self._validate_output(out, 'dc')
        return out

    def export_geojson(self, book: Any, path: str) -> str:
        out = export_geojson_annotations(book, path)
        self._validate_output(out, 'geojson')
        return out

    def export_bundle(self, book: Any, folder: str) -> dict:
        """Genera conjunto básico de exportaciones en carpeta destino y devuelve mapa de rutas."""
        base = Path(folder); base.mkdir(parents=True, exist_ok=True)
        outputs = {}
        outputs['pdf'] = self.export_pdf(book, str(base/'book.pdf'))
        outputs['iiif'] = self.export_iiif(book, str(base/'manifest.json'))
        outputs['tei'] = self.export_tei(book, str(base/'book.xml'))
        outputs['dc'] = self.export_dublin_core(book, str(base/'dublin_core.json'))
        outputs['geojson'] = self.export_geojson(book, str(base/'annotations.geojson'))
        # Adjunta resumen de validaciones
        outputs['__summary__'] = self.validation_report
        return outputs

    # === Validación post-export ===
    def __init__(self):
        self.validation_report: Dict[str, Dict[str, Any]] = {}

    def _validate_output(self, path: str, fmt: str) -> None:
        try:
            p = Path(path)
            if not p.exists():
                self.validation_report[fmt] = {"exists": False, "error": "Archivo no creado"}
                return
            size = p.stat().st_size
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            record: Dict[str, Any] = {"exists": True, "size": size, "sha256": h}
            if fmt in ("iiif", "dc", "geojson"):
                try:
                    data = json.loads(p.read_text(encoding='utf-8'))
                    record['json_valid'] = True
                    # Chequeos mínimos de esquema
                    if fmt == 'iiif':
                        record['has_items'] = isinstance(data.get('items'), list)
                    elif fmt == 'dc':
                        record['has_title'] = 'title' in data
                    elif fmt == 'geojson':
                        record['type_ok'] = data.get('type') == 'FeatureCollection'
                except Exception as je:
                    record['json_valid'] = False
                    record['error'] = f"JSON inválido: {je}"  # pragma: no cover
            if fmt == 'tei':
                try:
                    etree.fromstring(p.read_bytes())
                    record['xml_wellformed'] = True
                except Exception as xe:
                    record['xml_wellformed'] = False
                    record['error'] = f"XML inválido: {xe}"  # pragma: no cover
            self.validation_report[fmt] = record
        except Exception as e:
            self.validation_report[fmt] = {"exists": False, "error": str(e)}  # pragma: no cover
