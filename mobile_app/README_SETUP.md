# GeoDocs Scanner - Mobile App Setup Guide

## Quick Start

### 1\. Start the Desktop Server

From the project root directory:

```
# Activate virtual environment (Windows)
& ".venv\Scripts\Activate.ps1"
#Install requirements
pip install -r requirements.txt
# Start the mobile API server
python start_mobile_server.py
```

**Alternative: Start from Launcher**

```
python launcher.py
```

Then click "📶 Iniciar Servidor Móvil" or "📡 Iniciar con logs (consola)".

**Server Options:**

*   **Default**: Runs on port 5000 with mDNS discovery
*   **With logs**: See console output for debugging
*   **Log level**: Set via env var `GEODOCS_LOG_LEVEL=DEBUG` (DEBUG/INFO/WARNING/ERROR)
*   **Colored logs**: Set `GEODOCS_COLOR_LOGS=1` for ANSI colors in console

```
# Example: Start with debug logs and colors
$env:GEODOCS_LOG_LEVEL="DEBUG"; $env:GEODOCS_COLOR_LOGS="1"; python start_mobile_server.py
```

The server will display:

```
============================================================
GeoDocs Scanner - Mobile API Server
============================================================

Mobile devices can now discover this server automatically
Or connect manually to: http://[your-ip]:5000

Press Ctrl+C to stop the server
```

**Server Features:**

*   mDNS discovery (service name: `_geodocs._tcp.local.`)
*   REST API endpoints for documents, pages, OCR
*   WebSocket for real-time sync
*   Image serving for captured pages
*   Annotations sync (batch push/pull)

---

### 2\. Run the Flutter Mobile App

#### Prerequisites

Install Flutter SDK: https://docs.flutter.dev/get-started/install

Verify installation:

```
flutter doctor
```

#### Setup

Navigate to the mobile app directory:

```
cd mobile_app
```

Install dependencies:

```
flutter pub get
```

#### Run on Android Emulator

Start an emulator from Android Studio or:

```
# List available emulators
emulator -list-avds

# Start an emulator
emulator -avd <emulator-name>
```

Then run:

```
flutter run
```

#### Run on Physical Android Device

##### 1\. Enable USB Debugging on your phone

**On your Android device:**

*   Go to **Settings** → **About phone**
*   Tap **Build number** 7 times (enables Developer mode)
*   Go back and enter **Developer options**
*   Enable **USB debugging**

##### 2\. Connect phone via USB

Connect your phone to the PC with a USB cable. When prompted "Allow USB debugging?", accept and check "Always allow from this computer".

##### 3\. Verify Flutter detects the device

```
cd mobile_app
flutter devices
```

You should see something like:

```
SM-G973F (mobile)         • 1234567890ABCDEF • android-arm64 • Android 12 (API 31)
```

##### 4\. Run the app

```
flutter run
```

Or specify the device:

```
flutter run -d 1234567890ABCDEF
```

##### Alternative: Run via WiFi (Android)

After connecting via USB once:

```
# Get device IP address
adb shell ip -f inet addr show wlan0

# Connect via TCP (port 5555)
adb tcpip 5555
adb connect <DEVICE-IP>:5555

# Disconnect USB cable and run
cd mobile_app
flutter run
```

#### Run on iOS (macOS only)

##### Physical iPhone/iPad:

1.  **Connect device via USB**
2.  **Trust the Mac** - Accept "Trust this computer" on iPhone
3.  **Configure development team in Xcode:**

```
cd mobile_app
open ios/Runner.xcworkspace
```

In Xcode:

*   Select **Runner** project
*   Go to **Signing & Capabilities**
*   Select your **Team** (Apple account)

1.  **Run the app:**

```
flutter run
```

##### iOS Simulator:

```
# Open iOS simulator
open -a Simulator

# Run app
flutter run
```

#### Build APK (Android)

```
flutter build apk --release
```

The APK will be at: `build/app/outputs/flutter-apk/app-release.apk`

#### Build for iOS (macOS only)

```
flutter build ios --release
```

---

## Mobile App Flow

1.  **Server Discovery**: App automatically finds the desktop server via mDNS
2.  **Connect**: Tap a discovered server to authenticate
3.  **Home**: View documents list
4.  **Capture**: Take photos of pages (auto-upload)
5.  **Documents**: Browse pages, view OCR
6.  **OCR Correction**: Edit and correct OCR text
7.  **Annotations**: Create/edit/delete annotations with offline queue
8.  **Sync**: Background sync every 10 seconds

---

## Troubleshooting

### Server not discovered

**Check firewall**: Allow port 5000 and mDNS (port 5353 UDP)

**Manual connection**: Use server IP instead of discovery

*   Edit `lib/services/server_discovery_service.dart`
*   Or add manual entry option in the app

### Connection refused

**Verify server is running**:

```
# Check if server is listening
netstat -an | findstr :5000
```

**Check network**: Device and server must be on the same network

### Dependencies missing

**Install Python requirements**:

```
pip install -r requirements.txt
```

**Install Flutter packages**:

```
cd mobile_app
flutter pub get
```

### Physical Device Issues

**"No devices found":**

*   Verify USB debugging is enabled on device
*   Try a different USB cable (data cable, not charge-only)
*   Install USB drivers for your device manufacturer (Windows)
*   Run `adb devices` to verify ADB detection
*   Try `adb kill-server` then `adb start-server`

**"Unauthorized device":**

*   Disconnect and reconnect the device
*   Revoke USB debugging authorizations in Developer options
*   Reconnect and accept the authorization prompt again

**"Installation blocked":**

*   On Android, enable installation from unknown sources
*   Accept the install prompt when it appears on your device
*   Check if "Install via USB" is enabled in Developer options

**App crashes on startup:**

*   Check minimum SDK version in `android/app/build.gradle`
*   Verify device meets minimum requirements
*   Run `flutter clean` and rebuild
*   Check device logs: `flutter logs`

### zeroconf warning

If you see "zeroconf not available", install it:

```
pip install zeroconf
```

The server will still work, but mDNS discovery won't be available.

---

## Log Files

Server logs are saved to: `logs/mobile_server_YYYYMMDD-HHMMSS.log`

**Open logs folder** from launcher or manually:

```
explorer logs
```

---

## Advanced Configuration

### Change Server Port

Edit `services/mobile_api_server.py`:

```python
SERVICE_PORT = 5000  # Change to desired port
```

### Configure mDNS Service Name

Edit `services/mobile_api_server.py`:

```python
SERVICE_NAME = "GeoDocs Scanner"  # Change to custom name
SERVICE_TYPE = "_geodocs._tcp.local."
```

### Server Endpoints

*   `POST /api/auth/token` - Authenticate and get token
*   `GET /api/documents` - List documents
*   `GET /api/pages/<doc_id>` - Get pages for document
*   `POST /api/capture` - Upload captured image
*   `POST /api/ocr/correct` - Submit OCR correction
*   `POST /api/annotations` - Create annotation
*   `POST /api/annotations/batch` - Batch upload annotations
*   `GET /api/annotations/changes?since=<ISO_timestamp>` - Get changes since timestamp
*   `GET /api/changes` - Get all changes
*   `GET /images/<doc_id>/<filename>` - Serve page image

### WebSocket Events

**Client → Server:**

*   `authenticate` - Send token
*   `ocr_correction` - Submit OCR edit

**Server → Client:**

*   `page_uploaded` - New page captured
*   `ocr_completed` - OCR processing done
*   `ocr_corrected` - OCR text updated
*   `annotation_added` - New annotation created
*   `error` - Error notification

---

## Development

### Run Tests

Server tests:

```
pytest tests/test_mobile_annotations_sync.py -v
```

All tests:

```
pytest -v
```

### Hot Reload (Flutter)

While the app is running, use these commands in the terminal:

*   `**r**` → Hot reload (reloads changed code, preserves state)
*   `**R**` → Hot restart (restarts app, resets state)
*   `**q**` → Quit/Stop app
*   `**d**` → Detach (keeps app running, stops debugging)
*   `**h**` → Show all available commands

**Tips:**

*   Hot reload works for most UI changes
*   Use hot restart for changes to `main()`, global variables, or state initialization
*   Some changes require a full rebuild (native code, pubspec.yaml, assets)

---

## Production Deployment

### Server

Use a production WSGI server:

```
pip install gunicorn  # Linux/macOS
# or use waitress on Windows
pip install waitress

waitress-serve --host=0.0.0.0 --port=5000 services.mobile_api_server:app
```

### Mobile App

Build signed release:

**Android:**

```
# Generate keystore (first time only)
keytool -genkey -v -keystore release-key.jks -keyalg RSA -keysize 2048 -validity 10000 -alias geodocs

# Build signed APK
flutter build apk --release
```

**iOS:**

```
# Configure signing in Xcode
open ios/Runner.xcworkspace

# Build
flutter build ios --release
```

---

## Support

For issues, check:

*   Server logs in `logs/` folder
*   Mobile app console output
*   Network connectivity between devices
*   Firewall/antivirus settings

Documentation: See `docs/mobile_app_integration.md` for technical details