
def export_bundle(db_path: str, document_id: int, out_dir: str, base_img_url: str = ""):
    from pathlib import Path
    from .iiif import export_iiif
    from .tei import export_tei
    from .dc import export_dc
    from .geojson import export_geojson
    manifest = export_iiif(db_path, document_id, out_dir, base_img_url=base_img_url)
    tei = export_tei(db_path, document_id, out_dir)
    dc = export_dc(db_path, document_id, out_dir)
    geo = export_geojson(db_path, document_id, out_dir)
    return {"iiif": manifest, "tei": tei, "dc": dc, "geojson": geo}


def export_bundle_zip(db_path: str, document_id: int, out_dir: str, base_img_url: str = ""):
    from pathlib import Path
    import zipfile, os
    res = export_bundle(db_path, document_id, out_dir, base_img_url=base_img_url)
    zip_path = Path(out_dir) / f"geodocs_bundle_doc_{document_id}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for k,v in res.items():
            if v and os.path.exists(v): z.write(v, arcname=Path(v).name)
    return str(zip_path), res
