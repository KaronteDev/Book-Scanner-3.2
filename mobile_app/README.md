# GeoDocs Mobile

Flutter mobile companion app for GeoDocs Scanner.

## Features

- **High-quality capture** from smartphone camera
- **WiFi synchronization** with desktop server (mDNS discovery)
- **OCR correction** interface for tablets
- **Real-time updates** via WebSocket
- **Offline support** with local caching

## Requirements

- Flutter SDK 3.0+
- iOS 12+ / Android 6+
- Desktop running GeoDocs Scanner server

## Installation

```bash
cd mobile_app
flutter pub get
flutter run
```

## Architecture

- **Flutter** (iOS/Android client)
- **Provider** for state management
- **mDNS** for server discovery
- **REST API** for data sync
- **WebSocket** for real-time events

## API Endpoints

The mobile app communicates with these server endpoints:

- `POST /api/auth/token` - Authenticate device
- `POST /api/capture` - Upload captured image
- `GET /api/documents` - List documents
- `GET /api/pages/:docId` - Get document pages
- `POST /api/ocr/correct` - Submit OCR corrections
- `POST /api/annotations` - Add annotations
- `WS /sync` - WebSocket for real-time updates

## Usage

1. Launch GeoDocs Scanner on desktop
2. Open mobile app
3. App auto-discovers server via mDNS
4. Connect to server
5. Capture pages with camera
6. Review and correct OCR on tablet

## Roadmap

- ✅ Phase 1: Basic capture + upload
- ✅ Phase 2: Page list + OCR correction
- ✅ Phase 3: Advanced annotations + incremental sync
- 📋 Phase 4: Presentation mode (read-only + 3D remote control)

## License

MIT
