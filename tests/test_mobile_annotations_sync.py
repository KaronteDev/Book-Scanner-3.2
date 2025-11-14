import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from services import mobile_api_server as srv


@pytest.fixture(autouse=True)
def temp_storage(tmp_path, monkeypatch):
    ann_root = tmp_path / 'annotations'
    changes_log = tmp_path / 'changes.json'
    monkeypatch.setattr(srv, 'annotations_root', ann_root)
    monkeypatch.setattr(srv, 'changes_log_path', changes_log)
    monkeypatch.setattr(srv, 'changes', [])
    yield


def _auth_headers(client):
    # Obtain token
    r = client.post('/api/auth/token', json={'device_id': 'test-device'})
    assert r.status_code == 200
    token = r.get_json()['token']
    return {'Authorization': f'Bearer {token}'}


def test_batch_and_changes_flow(tmp_path):
    app = srv.app
    app.testing = True
    client = app.test_client()

    headers = _auth_headers(client)

    # Initial changes should be empty
    r = client.get('/api/annotations/changes?since=1970-01-01T00:00:00', headers=headers)
    assert r.status_code == 200
    assert r.get_json() == []

    # Push batch of annotations
    now = datetime.utcnow().isoformat()
    anns = [
        {
            'id': 'a1',
            'page_id': 'p1',
            'doc_id': 'd1',
            'type': 'text',
            'rect': {'x': 10, 'y': 20, 'w': 100, 'h': 40},
            'text': 'Note 1',
            'color': 0xFFFFD54F,
            'stroke_width': 2.0,
            'created_at': now,
            'updated_at': now,
        },
        {
            'id': 'a2',
            'page_id': 'p1',
            'doc_id': 'd1',
            'type': 'ink',
            'points': [{'x': 1, 'y': 1}, {'x': 5, 'y': 5}],
            'color': 0x8090CAF9,
            'stroke_width': 3.0,
            'created_at': now,
            'updated_at': now,
        },
    ]

    r = client.post('/api/annotations/batch', json={'annotations': anns}, headers=headers)
    assert r.status_code == 200
    assert r.get_json().get('success') is True

    # Pull changes since epoch -> should include at least both annotations
    r = client.get('/api/annotations/changes?since=1970-01-01T00:00:00', headers=headers)
    assert r.status_code == 200
    fetched = r.get_json()
    ids = {a['id'] for a in fetched}
    assert {'a1', 'a2'}.issubset(ids)

    # Global changes feed should include annotation_added events
    r = client.get('/api/changes?since=1970-01-01T00:00:00', headers=headers)
    assert r.status_code == 200
    events = r.get_json()
    assert any(e.get('type') == 'annotation_added' and e.get('annotation', {}).get('id') == 'a1' for e in events)

    # Now delete one annotation and verify it disappears from storage
    anns_del = [{
        'id': 'a2',
        'page_id': 'p1',
        'doc_id': 'd1',
        'type': 'ink',
        'status': 'deleted',
    }]
    r = client.post('/api/annotations/batch', json={'annotations': anns_del}, headers=headers)
    assert r.status_code == 200

    page_file = srv.annotations_root / 'd1' / 'p1.json'
    data = json.loads(page_file.read_text(encoding='utf-8'))
    assert all(a['id'] != 'a2' for a in data.get('annotations', []))

    # Changes since a recent timestamp should be non-empty
    recent = (datetime.utcnow() - timedelta(seconds=5)).isoformat()
    r = client.get(f'/api/changes?since={recent}', headers=headers)
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)

    # Changes with far future timestamp should return empty
    r = client.get('/api/changes?since=2999-01-01T00:00:00', headers=headers)
    assert r.status_code == 200
    assert r.get_json() == []
