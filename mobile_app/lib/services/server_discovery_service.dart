import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:nsd/nsd.dart';
import '../models/server_info.dart';

class ServerDiscoveryService extends ChangeNotifier {
  final Discovery _discovery = getNsd();
  final List<ServerInfo> _servers = [];
  bool _isDiscovering = false;

  List<ServerInfo> get servers => List.unmodifiable(_servers);
  bool get isDiscovering => _isDiscovering;

  Future<void> startDiscovery() async {
    if (_isDiscovering) return;

    _isDiscovering = true;
    _servers.clear();
    notifyListeners();

    try {
      final stream = await _discovery.discoverServices('_geodocs._tcp');
      
      stream.listen(
        (service) {
          if (service.name != null && service.host != null && service.port != null) {
            final serverInfo = ServerInfo(
              host: service.host!,
              port: service.port!,
              name: service.name!,
            );
            
            // Avoid duplicates
            if (!_servers.any((s) => s.host == serverInfo.host && s.port == serverInfo.port)) {
              _servers.add(serverInfo);
              notifyListeners();
            }
          }
        },
        onError: (error) {
          debugPrint('Discovery error: $error');
        },
      );
    } catch (e) {
      debugPrint('Failed to start discovery: $e');
      _isDiscovering = false;
      notifyListeners();
    }
  }

  Future<void> stopDiscovery() async {
    if (!_isDiscovering) return;

    try {
      await _discovery.stopDiscovery();
    } catch (e) {
      debugPrint('Failed to stop discovery: $e');
    }

    _isDiscovering = false;
    notifyListeners();
  }

  void clearServers() {
    _servers.clear();
    notifyListeners();
  }

  @override
  void dispose() {
    stopDiscovery();
    super.dispose();
  }
}
