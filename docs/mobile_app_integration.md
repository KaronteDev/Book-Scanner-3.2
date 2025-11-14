# GeoDocs Scanner - Mobile App Integration Guide

## Overview

The mobile app provides high-quality document capture from smartphones and OCR correction capabilities on tablets, syncing directly with the desktop application over WiFi.

## Architecture

### Mobile App (Flutter)
- **Platform**: iOS 12+ / Android 6+
- **State Management**: Provider
- **Features**:
  - mDNS server auto-discovery
  - Camera capture with high resolution
  - Real-time WebSocket sync
  - OCR text correction interface
  - Offline support with local caching

### Desktop Server (Flask)
- **API**: RESTful endpoints for data exchange
- **WebSocket**: Real-time event notifications
- **Discovery**: mDNS/Bonjour for auto-discovery
- **Security**: Token-based authentication

## Setup Instructions

### Desktop Server Setup

1. **Install dependencies**:
```bash
cd "M:\Trabajo Privado\FAT\Book Scanner 3.2"
.\.venv\Scripts\Activate.ps1
pip install flask-socketio flask-cors zeroconf python-socketio
```

2. **Start the mobile API server**:
```bash
python start_mobile_server.py
```

The server will:
- Start on port 5000
- Register mDNS service as "GeoDocs Scanner"
- Accept connections from mobile devices on local network

### Mobile App Setup

1. **Install Flutter** (if not already installed):
   - Download from https://flutter.dev/docs/get-started/install
   - Add to PATH

2. **Navigate to mobile app**:
```bash
cd mobile_app
```

3. **Install dependencies**:
```bash
flutter pub get
```

4. **Run on device/emulator**:
```bash
# For Android
flutter run

# For iOS (macOS only)
flutter run -d ios

# For specific device
flutter devices
flutter run -d <device-id>
```

## Usage Flow

### 1. Server Discovery
- Mobile app automatically scans for servers using mDNS
- Servers appear in discovery screen
- Tap server to connect

### 2. Authentication
- App requests token from server
- Token stored locally for subsequent requests
- Token valid for 24 hours

### 3. Document Capture
1. Tap camera button
2. Take photo of document page
3. Image uploaded automatically
4. Server processes and runs OCR
5. Real-time notification when OCR complete

### 4. OCR Correction
1. View document pages
2. Tap completed page
3. Edit OCR text
4. Save corrections (synced to server)

## API Endpoints

### Authentication
- `POST /api/auth/token` - Get authentication token
  ```json
  Request: {"device_id": "unique-device-id"}
  Response: {"token": "...", "expires_in": 86400}
  ```

### Documents & Pages
- `GET /api/health` - Server health check
- `GET /api/documents` - List all documents
- `GET /api/pages/:docId` - Get pages for document
- `POST /api/capture` - Upload captured image
  ```
  Form data: {doc_id, image: file}
  ```

### OCR & Annotations
- `POST /api/ocr/correct` - Submit OCR correction
  ```json
  {"page_id": "...", "text": "corrected text"}
  ```
- `POST /api/annotations` - Add a single annotation
  ```json
  {"page_id": "...", "annotation": {...}}
  ```
- `POST /api/annotations/batch` - Add multiple annotations (offline queue push)
  ```json
  {"annotations": [{...}, {...}]}
  ```
- `GET /api/annotations/changes?since=<iso>` - Fetch annotations updated since timestamp

### Images
- `GET /images/:docId/:filename` - Serve captured page images for annotation overlay

### WebSocket Events
- `WS /sync` - Real-time sync channel

**Client → Server**:
```json
{"type": "auth", "token": "..."}
```

**Server → Client**:
```json
{"type": "page_uploaded", "id": "...", "status": "processing"}
{"type": "ocr_completed", "id": "...", "ocr_text": "..."}
{"type": "ocr_corrected", "page_id": "...", "text": "..."}
{"type": "annotation_added", "id": "...", "page_id": "..."}
{"type": "error", "message": "..."}
```

## Network Requirements

### Firewall
Ensure port 5000 is open for:
- HTTP (REST API)
- WebSocket
- mDNS (UDP port 5353)

### Same Network
Desktop and mobile devices must be on the same local network (WiFi/LAN).

### Manual Connection
If mDNS discovery fails:
1. Find desktop IP: `ipconfig` (Windows) / `ifconfig` (Mac/Linux)
2. Add manual connection in app (future feature)
3. Or use: `http://[desktop-ip]:5000`

## Security Considerations

### Current Implementation (Development)
- Token-based authentication
- Local network only
- No encryption

### Production Recommendations
- Enable HTTPS/TLS for API
- Use WSS (WebSocket Secure)
- Implement certificate pinning
- Add rate limiting
- Store tokens securely (iOS Keychain / Android Keystore)
- Add token refresh mechanism
- Implement device registration/approval

## Troubleshooting

### Server not discovered
- Check firewall settings
- Verify both devices on same network
- Check if mDNS/Bonjour is enabled
- Install zeroconf: `pip install zeroconf`

### Connection failed
- Verify server is running: `python start_mobile_server.py`
- Check server logs for errors
- Ensure port 5000 not blocked
- Try manual IP connection

### Upload fails
- Check network connection
- Verify token not expired
- Check server disk space
- Review server logs

### OCR not working
- Ensure Tesseract installed on server
- Check image quality/resolution
- Verify server processing capacity

## Development

### Mobile App Structure
```
mobile_app/
├── lib/
│   ├── main.dart                 # App entry point
│   ├── models/                   # Data models
│   │   ├── document.dart
│   │   ├── page.dart
│   │   ├── annotation.dart
│   │   └── server_info.dart
│   ├── services/                 # Business logic
│   │   ├── api_service.dart
│   │   ├── server_discovery_service.dart
│   │   ├── websocket_service.dart
│   │   ├── annotation_service.dart     # Local store + offline queue
│   │   └── sync_service.dart           # Background incremental sync
│   ├── screens/                  # UI screens
│   │   ├── capture_screen.dart
│   │   ├── home_screen.dart
│   │   ├── server_discovery_screen.dart
│   │   ├── document_pages_screen.dart
│   │   ├── ocr_correction_screen.dart
│   │   └── annotation_editor_screen.dart
│   └── widgets/                  # Reusable components
│       └── server_list_item.dart
└── pubspec.yaml                  # Dependencies
```

### Adding Features

#### New API Endpoint
1. Add route in `services/mobile_api_server.py`
2. Add method in `lib/services/api_service.dart`
3. Call from UI screen

#### New WebSocket Event
1. Emit from server: `socketio.emit('event_name', data)`
2. Listen in app: `wsService.events.listen((event) {...})`

## Roadmap

### Phase 1 ✅ (Completed)
- Basic capture and upload
- Server discovery via mDNS
- Token authentication

### Phase 2 ✅ (Completed)
- Page list view
- OCR correction interface
- WebSocket real-time updates

### Phase 3 ✅ (Completed)
- Advanced annotations (ink, highlights, text notes)
- Incremental sync (since=timestamp API + WS)
- Offline queue for annotations
- Image serving for overlay

### Phase 4 (Future)
- Presentation mode (tablet remote viewer)
- 3D page flip animations
- Collaborative editing
- Cloud backup integration

## License

MIT License - Same as main GeoDocs Scanner project
