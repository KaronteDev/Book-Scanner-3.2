"""
Flask REST API server for mobile app synchronization
Provides endpoints for capture, OCR correction, and real-time updates
"""

import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_file, abort
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import secrets
from functools import wraps

# Import existing services
import sys
sys.path.append(str(Path(__file__).parent.parent))
from services.export_service import ExportService
from services.ocr_service import OCRService

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Token storage (in-memory for now, should be Redis/DB in production)
active_tokens = {}
changes_log_path = Path('output_mobile') / 'changes.json'
annotations_root = Path('output_mobile') / 'annotations'
changes = []

# Load existing changes on startup
try:
    if changes_log_path.exists():
        changes = json.loads(changes_log_path.read_text(encoding='utf-8'))
except Exception:
    changes = []

# Service directory for mDNS
SERVICE_TYPE = '_geodocs._tcp.local.'
SERVICE_NAME = 'GeoDocs Scanner'
SERVICE_PORT = 5000


def generate_token(device_id: str) -> str:
    """Generate authentication token for device"""
    token = secrets.token_urlsafe(32)
    active_tokens[token] = {
        'device_id': device_id,
        'created_at': datetime.now().isoformat()
    }
    return token


def require_token(f):
    """Decorator to require valid token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid token'}), 401
        
        token = auth_header.split(' ')[1]
        
        if token not in active_tokens:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'service': SERVICE_NAME})


@app.route('/api/auth/token', methods=['POST'])
def get_token():
    """Authenticate device and get token"""
    data = request.json
    device_id = data.get('device_id')
    
    if not device_id:
        return jsonify({'error': 'device_id required'}), 400
    
    token = generate_token(device_id)
    
    return jsonify({
        'token': token,
        'expires_in': 86400  # 24 hours
    })


@app.route('/api/documents', methods=['GET'])
@require_token
def get_documents():
    """Get list of all documents"""
    # This should interface with your existing document storage
    # For now, returning mock data
    documents = [
        {
            'id': 'doc_1',
            'title': 'Sample Document',
            'created_at': datetime.now().isoformat(),
            'page_count': 5
        }
    ]
    
    return jsonify(documents)


@app.route('/api/pages/<doc_id>', methods=['GET'])
@require_token
def get_pages(doc_id):
    """Get pages for a specific document"""
    # This should interface with your existing page storage
    # Mock data for now
    pages = [
        {
            'id': f'page_{i}',
            'doc_id': doc_id,
            'page_number': i,
            'image_path': f'/images/{doc_id}/page_{i}.jpg',
            'ocr_text': f'Sample OCR text for page {i}',
            'status': 'completed',
            'created_at': datetime.now().isoformat()
        }
        for i in range(1, 6)
    ]
    
    return jsonify(pages)


@app.route('/api/capture', methods=['POST'])
@require_token
def upload_capture():
    """Upload captured image from mobile device"""
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    doc_id = request.form.get('doc_id', 'default')
    image_file = request.files['image']
    
    # Create directory structure
    output_dir = Path('output_mobile') / doc_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique page ID
    page_id = str(uuid.uuid4())
    page_number = len(list(output_dir.glob('*.jpg'))) + 1
    
    # Save image
    image_path = output_dir / f'page_{page_number}_{page_id}.jpg'
    image_file.save(str(image_path))
    
    # Create page record
    page_data = {
        'id': page_id,
        'doc_id': doc_id,
        'page_number': page_number,
        'image_path': str(image_path),
        'status': 'processing',
        'created_at': datetime.now().isoformat()
    }
    
    # Emit WebSocket event and record change
    socketio.emit('page_uploaded', page_data)
    _record_change({'type': 'page_uploaded', 'page': page_data})
    
    # Process OCR in background (async)
    socketio.start_background_task(_process_ocr, page_id, image_path)
    
    return jsonify(page_data), 201


def _process_ocr(page_id: str, image_path: Path):
    """Background task to process OCR"""
    try:
        # Here you would call your existing OCR service
        # For now, simulating processing
        import time
        time.sleep(2)
        
        ocr_text = "Processed OCR text would appear here"
        
        # Update page status
        page_data = {
            'id': page_id,
            'status': 'completed',
            'ocr_text': ocr_text
        }
        
        # Emit completion event
        socketio.emit('ocr_completed', page_data)
        _record_change({'type': 'ocr_completed', 'page': page_data})
        
    except Exception as e:
        socketio.emit('error', {
            'page_id': page_id,
            'message': str(e)
        })


@app.route('/api/ocr/correct', methods=['POST'])
@require_token
def correct_ocr():
    """Submit OCR correction from mobile device"""
    data = request.json
    page_id = data.get('page_id')
    corrected_text = data.get('text')
    
    if not page_id or corrected_text is None:
        return jsonify({'error': 'page_id and text required'}), 400
    
    # Here you would update the OCR text in your storage
    # For now, just emit event
    payload = {'page_id': page_id, 'text': corrected_text}
    socketio.emit('ocr_corrected', payload)
    _record_change({'type': 'ocr_corrected', 'data': payload})
    
    return jsonify({'success': True})


@app.route('/api/annotations', methods=['POST'])
@require_token
def add_annotation():
    """Add annotation from mobile device"""
    data = request.json
    page_id = data.get('page_id')
    annotation = data.get('annotation')
    
    if not page_id or not annotation:
        return jsonify({'error': 'page_id and annotation required'}), 400
    
    # Store single annotation via common batch handler
    ann = {
        'id': str(uuid.uuid4()),
        'page_id': page_id,
        'type': annotation.get('type', 'ink'),
        'points': annotation.get('points'),
        'rect': annotation.get('rect'),
        'text': annotation.get('text'),
        'color': annotation.get('color', 0xFFFFD54F),
        'stroke_width': annotation.get('stroke_width', 3.0),
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'status': 'synced',
    }
    _store_annotations([ann])
    socketio.emit('annotation_added', ann)
    _record_change({'type': 'annotation_added', 'annotation': ann})
    return jsonify(ann), 201


@app.route('/api/annotations/batch', methods=['POST'])
@require_token
def add_annotations_batch():
    data = request.json or {}
    anns = data.get('annotations', [])
    if not isinstance(anns, list) or not anns:
        return jsonify({'error': 'annotations array required'}), 400
    stored = _store_annotations(anns)
    for ann in stored:
        socketio.emit('annotation_added', ann)
        _record_change({'type': 'annotation_added', 'annotation': ann})
    return jsonify({'success': True, 'count': len(stored)})


@app.route('/api/annotations/changes')
@require_token
def annotations_changes():
    since_iso = request.args.get('since')
    try:
        since = datetime.fromisoformat(since_iso) if since_iso else datetime.fromtimestamp(0)
    except Exception:
        since = datetime.fromtimestamp(0)
    results = []
    for doc_dir in annotations_root.glob('*'):
        for page_file in doc_dir.glob('*.json'):
            try:
                data = json.loads(page_file.read_text(encoding='utf-8'))
            except Exception:
                continue
            for ann in data.get('annotations', []):
                try:
                    updated = datetime.fromisoformat(ann.get('updated_at'))
                except Exception:
                    continue
                if updated > since:
                    results.append(ann)
    return jsonify(results)


@app.route('/api/changes')
@require_token
def changes_feed():
    since_iso = request.args.get('since')
    try:
        since = datetime.fromisoformat(since_iso) if since_iso else datetime.fromtimestamp(0)
    except Exception:
        since = datetime.fromtimestamp(0)
    return jsonify([c for c in changes if datetime.fromisoformat(c['ts']) > since])


@app.route('/images/<doc_id>/<path:filename>')
def serve_image(doc_id, filename):
    # Serve images saved under output_mobile/<doc_id>/
    base = Path('output_mobile') / doc_id
    target = (base / filename).resolve()
    if not str(target).startswith(str(base.resolve())):
        return abort(403)
    if not target.exists():
        return abort(404)
    return send_file(str(target))


@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    print('Client connected')


@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    print('Client disconnected')


@socketio.on('auth')
def handle_auth(data):
    """Authenticate WebSocket connection"""
    token = data.get('token')
    
    if token in active_tokens:
        emit('auth_success', {'message': 'Authenticated'})
    else:
        emit('auth_failed', {'message': 'Invalid token'})


def _store_annotations(anns):
    annotations_root.mkdir(parents=True, exist_ok=True)
    stored = []
    for ann in anns:
        page_id = ann.get('page_id')
        doc_id = ann.get('doc_id') or 'default'
        doc_dir = annotations_root / doc_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        page_file = doc_dir / f'{page_id}.json'
        payload = {'annotations': []}
        if page_file.exists():
            try:
                payload = json.loads(page_file.read_text(encoding='utf-8'))
            except Exception:
                payload = {'annotations': []}
        # Update timestamps and ensure id
        ann['id'] = ann.get('id') or str(uuid.uuid4())
        now_iso = datetime.now().isoformat()
        ann['created_at'] = ann.get('created_at') or now_iso
        ann['updated_at'] = now_iso
        ann['status'] = ann.get('status') or 'synced'
        # Replace or delete if exists
        payload['annotations'] = [a for a in payload['annotations'] if a.get('id') != ann['id']]
        if ann['status'] != 'deleted':
            payload['annotations'].append(ann)
        page_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        stored.append(ann)
    return stored


def _record_change(obj):
    global changes
    changes_log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {'ts': datetime.now().isoformat(), **obj}
    changes.append(entry)
    try:
        changes_log_path.write_text(json.dumps(changes, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass


def start_mdns_service():
    """Start mDNS service for auto-discovery"""
    try:
        from zeroconf import ServiceInfo, Zeroconf
        import socket
        
        # Get local IP
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        info = ServiceInfo(
            SERVICE_TYPE,
            f"{SERVICE_NAME}.{SERVICE_TYPE}",
            addresses=[socket.inet_aton(local_ip)],
            port=SERVICE_PORT,
            properties={'version': '1.0'},
        )
        
        zeroconf = Zeroconf()
        zeroconf.register_service(info)
        
        print(f"mDNS service registered: {SERVICE_NAME} at {local_ip}:{SERVICE_PORT}")
        
        return zeroconf
        
    except ImportError:
        print("Warning: zeroconf not installed. mDNS discovery not available.")
        print("Install with: pip install zeroconf")
        return None


if __name__ == '__main__':
    # Start mDNS service
    zeroconf = start_mdns_service()
    
    try:
        # Run Flask-SocketIO server
        print(f"Starting {SERVICE_NAME} mobile API server...")
        print(f"Server available at: http://0.0.0.0:{SERVICE_PORT}")
        socketio.run(app, host='0.0.0.0', port=SERVICE_PORT, debug=True)
    finally:
        if zeroconf:
            zeroconf.unregister_all_services()
            zeroconf.close()
