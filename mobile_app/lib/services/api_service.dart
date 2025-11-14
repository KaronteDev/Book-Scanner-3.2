import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../models/server_info.dart';
import '../models/document.dart';
import '../models/page.dart';
import '../models/annotation.dart';

class ApiService extends ChangeNotifier {
  ServerInfo? _serverInfo;
  bool _isConnected = false;

  ServerInfo? get serverInfo => _serverInfo;
  bool get isConnected => _isConnected;

  // Connect to server and authenticate
  Future<bool> connect(ServerInfo server) async {
    try {
      final response = await http.post(
        Uri.parse('${server.baseUrl}/api/auth/token'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'device_id': await _getDeviceId()}),
      ).timeout(const Duration(seconds: 5));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        _serverInfo = server.copyWith(token: data['token']);
        _isConnected = true;
        await _saveServerInfo();
        notifyListeners();
        return true;
      }
    } catch (e) {
      debugPrint('Connection error: $e');
    }
    return false;
  }

  // Disconnect from server
  Future<void> disconnect() async {
    _serverInfo = null;
    _isConnected = false;
    await _clearServerInfo();
    notifyListeners();
  }

  // Restore connection from saved preferences
  Future<void> restoreConnection() async {
    final prefs = await SharedPreferences.getInstance();
    final serverJson = prefs.getString('server_info');
    
    if (serverJson != null) {
      try {
        final server = ServerInfo.fromJson(jsonDecode(serverJson));
        final isOnline = await _checkServerOnline(server);
        
        if (isOnline) {
          _serverInfo = server;
          _isConnected = true;
          notifyListeners();
        } else {
          await _clearServerInfo();
        }
      } catch (e) {
        debugPrint('Failed to restore connection: $e');
        await _clearServerInfo();
      }
    }
  }

  // Upload captured image
  Future<PageModel?> uploadCapture(String docId, File imageFile) async {
    if (_serverInfo == null) return null;

    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('${_serverInfo!.baseUrl}/api/capture'),
      );

      request.headers['Authorization'] = 'Bearer ${_serverInfo!.token}';
      request.fields['doc_id'] = docId;
      request.files.add(await http.MultipartFile.fromPath('image', imageFile.path));

      final response = await request.send().timeout(const Duration(seconds: 30));
      
      if (response.statusCode == 200 || response.statusCode == 201) {
        final responseData = await response.stream.bytesToString();
        final data = jsonDecode(responseData);
        return PageModel.fromJson(data);
      }
    } catch (e) {
      debugPrint('Upload error: $e');
    }
    return null;
  }

  // Get document pages
  Future<List<PageModel>> getPages(String docId) async {
    if (_serverInfo == null) return [];

    try {
      final response = await http.get(
        Uri.parse('${_serverInfo!.baseUrl}/api/pages/$docId'),
        headers: {
          'Authorization': 'Bearer ${_serverInfo!.token}',
        },
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        return data.map((json) => PageModel.fromJson(json)).toList();
      }
    } catch (e) {
      debugPrint('Get pages error: $e');
    }
    return [];
  }

  // Get documents
  Future<List<Document>> getDocuments() async {
    if (_serverInfo == null) return [];

    try {
      final response = await http.get(
        Uri.parse('${_serverInfo!.baseUrl}/api/documents'),
        headers: {
          'Authorization': 'Bearer ${_serverInfo!.token}',
        },
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        return data.map((json) => Document.fromJson(json)).toList();
      }
    } catch (e) {
      debugPrint('Get documents error: $e');
    }
    return [];
  }

  // Correct OCR text
  Future<bool> correctOcr(String pageId, String correctedText) async {
    if (_serverInfo == null) return false;

    try {
      final response = await http.post(
        Uri.parse('${_serverInfo!.baseUrl}/api/ocr/correct'),
        headers: {
          'Authorization': 'Bearer ${_serverInfo!.token}',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'page_id': pageId,
          'text': correctedText,
        }),
      ).timeout(const Duration(seconds: 10));

      return response.statusCode == 200;
    } catch (e) {
      debugPrint('OCR correction error: $e');
    }
    return false;
  }

  // Add annotation
  Future<bool> addAnnotation(String pageId, Map<String, dynamic> annotation) async {
    if (_serverInfo == null) return false;

    try {
      final response = await http.post(
        Uri.parse('${_serverInfo!.baseUrl}/api/annotations'),
        headers: {
          'Authorization': 'Bearer ${_serverInfo!.token}',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'page_id': pageId,
          'annotation': annotation,
        }),
      ).timeout(const Duration(seconds: 10));

      return response.statusCode == 200 || response.statusCode == 201;
    } catch (e) {
      debugPrint('Add annotation error: $e');
    }
    return false;
  }

  // Helper methods
  Future<String> _getDeviceId() async {
    final prefs = await SharedPreferences.getInstance();
    String? deviceId = prefs.getString('device_id');
    
    if (deviceId == null) {
      deviceId = DateTime.now().millisecondsSinceEpoch.toString();
      await prefs.setString('device_id', deviceId);
    }
    
    return deviceId;
  }

  Future<void> _saveServerInfo() async {
    if (_serverInfo == null) return;
    
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('server_info', jsonEncode(_serverInfo!.toJson()));
  }

  Future<void> _clearServerInfo() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('server_info');
  }

  Future<bool> _checkServerOnline(ServerInfo server) async {
    try {
      final response = await http.get(
        Uri.parse('${server.baseUrl}/api/health'),
      ).timeout(const Duration(seconds: 3));
      
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  // Push annotations in batch
  Future<bool> pushAnnotations(List<Annotation> anns) async {
    if (_serverInfo == null || anns.isEmpty) return false;

    try {
      final response = await http.post(
        Uri.parse('${_serverInfo!.baseUrl}/api/annotations/batch'),
        headers: {
          'Authorization': 'Bearer ${_serverInfo!.token}',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'annotations': anns.map((a) => a.toJson()).toList(),
        }),
      ).timeout(const Duration(seconds: 10));

      return response.statusCode == 200;
    } catch (e) {
      debugPrint('Push annotations error: $e');
    }
    return false;
  }

  // Fetch annotation changes since timestamp
  Future<List<Annotation>> fetchAnnotationChanges(DateTime since) async {
    if (_serverInfo == null) return [];

    try {
      final response = await http.get(
        Uri.parse('${_serverInfo!.baseUrl}/api/annotations/changes?since=${Uri.encodeComponent(since.toIso8601String())}'),
        headers: {
          'Authorization': 'Bearer ${_serverInfo!.token}',
        },
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        return data.map((j) => Annotation.fromJson(j)).toList();
      }
    } catch (e) {
      debugPrint('Fetch annotation changes error: $e');
    }
    return [];
  }

  // Helper to build page image URL
  String pageImageUrl(String docId, String fileName) {
    return '${_serverInfo!.baseUrl}/images/$docId/$fileName';
  }
}
