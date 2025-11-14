import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:provider/provider.dart';
import 'api_service.dart';
import 'annotation_service.dart';

class SyncService extends ChangeNotifier {
  Timer? _timer;
  bool _running = false;

  bool get running => _running;

  void start(context) {
    if (_running) return;
    _running = true;
    _timer = Timer.periodic(const Duration(seconds: 10), (_) async {
      try {
        final api = Provider.of<ApiService>(context, listen: false);
        final ann = Provider.of<AnnotationService>(context, listen: false);
        await ann.sync(api);
      } catch (e) {
        debugPrint('Sync tick error: $e');
      }
    });
  }

  void stop() {
    _timer?.cancel();
    _running = false;
  }

  @override
  void dispose() {
    stop();
    super.dispose();
  }
}
