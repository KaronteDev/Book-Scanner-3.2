import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../models/server_info.dart';

class WebSocketService extends ChangeNotifier {
  WebSocketChannel? _channel;
  StreamSubscription? _subscription;
  bool _isConnected = false;
  
  final _eventController = StreamController<Map<String, dynamic>>.broadcast();
  
  bool get isConnected => _isConnected;
  Stream<Map<String, dynamic>> get events => _eventController.stream;

  // Connect to WebSocket
  Future<void> connect(ServerInfo serverInfo) async {
    if (_isConnected) return;

    try {
      _channel = WebSocketChannel.connect(
        Uri.parse(serverInfo.wsUrl),
      );

      // Send authentication
      _channel!.sink.add(jsonEncode({
        'type': 'auth',
        'token': serverInfo.token,
      }));

      _subscription = _channel!.stream.listen(
        (message) {
          try {
            final data = jsonDecode(message as String);
            _eventController.add(data);
            _handleEvent(data);
          } catch (e) {
            debugPrint('WebSocket message parse error: $e');
          }
        },
        onError: (error) {
          debugPrint('WebSocket error: $error');
          _handleDisconnect();
        },
        onDone: () {
          debugPrint('WebSocket closed');
          _handleDisconnect();
        },
      );

      _isConnected = true;
      notifyListeners();
    } catch (e) {
      debugPrint('WebSocket connection error: $e');
      _handleDisconnect();
    }
  }

  // Disconnect from WebSocket
  Future<void> disconnect() async {
    await _subscription?.cancel();
    await _channel?.sink.close();
    _handleDisconnect();
  }

  // Send message
  void send(Map<String, dynamic> message) {
    if (_isConnected && _channel != null) {
      _channel!.sink.add(jsonEncode(message));
    }
  }

  void _handleEvent(Map<String, dynamic> event) {
    final type = event['type'] as String?;
    
    switch (type) {
      case 'page_processed':
        debugPrint('Page processed: ${event['page_id']}');
        break;
      case 'ocr_completed':
        debugPrint('OCR completed: ${event['page_id']}');
        break;
      case 'error':
        debugPrint('Server error: ${event['message']}');
        break;
      default:
        debugPrint('Unknown event type: $type');
    }
  }

  void _handleDisconnect() {
    _isConnected = false;
    _channel = null;
    _subscription = null;
    notifyListeners();
  }

  @override
  void dispose() {
    disconnect();
    _eventController.close();
    super.dispose();
  }
}
