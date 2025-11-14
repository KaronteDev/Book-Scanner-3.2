import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/annotation.dart';
import 'api_service.dart';

class AnnotationService extends ChangeNotifier {
  final List<Annotation> _annotations = [];
  final List<Annotation> _queue = [];
  DateTime? _lastSyncAt;

  List<Annotation> annotationsForPage(String pageId) =>
      _annotations.where((a) => a.pageId == pageId && a.status != 'deleted').toList();

  DateTime? get lastSyncAt => _lastSyncAt;

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    _lastSyncAt = prefs.getString('ann_last_sync') != null
        ? DateTime.tryParse(prefs.getString('ann_last_sync')!)
        : null;

    final stored = prefs.getString('annotations');
    if (stored != null) {
      try {
        final List<dynamic> data = jsonDecode(stored);
        _annotations
          ..clear()
          ..addAll(data.map((j) => Annotation.fromJson(j)));
      } catch (_) {}
    }

    final queued = prefs.getString('annotations_queue');
    if (queued != null) {
      try {
        final List<dynamic> data = jsonDecode(queued);
        _queue
          ..clear()
          ..addAll(data.map((j) => Annotation.fromJson(j)));
      } catch (_) {}
    }

    notifyListeners();
  }

  Future<void> _persist() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('annotations', jsonEncode(_annotations.map((a) => a.toJson()).toList()));
    await prefs.setString('annotations_queue', jsonEncode(_queue.map((a) => a.toJson()).toList()));
    await prefs.setString('ann_last_sync', (_lastSyncAt ?? DateTime.fromMillisecondsSinceEpoch(0)).toIso8601String());
  }

  void add(Annotation a, {bool enqueue = true}) {
    _annotations.removeWhere((x) => x.id == a.id);
    _annotations.add(a);
    if (enqueue) {
      _queue.add(a.copyWith(status: a.status));
    }
    notifyListeners();
    _persist();
  }

  void update(Annotation a) {
    add(a.copyWith(status: 'updated'));
  }

  void delete(String id, String pageId) {
    final existing = _annotations.firstWhere((x) => x.id == id, orElse: () => Annotation(
      id: id,
      pageId: pageId,
      type: 'ink',
      points: const [],
      rect: null,
      text: null,
      color: 0xFFFFD54F,
      strokeWidth: 3.0,
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
      status: 'deleted',
    ));
    add(existing.copyWith(status: 'deleted'));
  }

  Future<void> sync(ApiService api) async {
    // Push queue
    if (_queue.isNotEmpty && api.isConnected) {
      try {
        final ok = await api.pushAnnotations(_queue);
        if (ok) {
          _queue.clear();
        }
      } catch (e) {
        debugPrint('Push annotations failed: $e');
      }
    }

    // Pull changes since last sync
    if (api.isConnected) {
      try {
        final since = _lastSyncAt ?? DateTime.fromMillisecondsSinceEpoch(0);
        final changes = await api.fetchAnnotationChanges(since);
        if (changes.isNotEmpty) {
          for (final ann in changes) {
            _annotations.removeWhere((x) => x.id == ann.id);
            _annotations.add(ann.copyWith(status: 'synced'));
          }
          _lastSyncAt = DateTime.now();
        }
      } catch (e) {
        debugPrint('Pull annotations failed: $e');
      }
    }

    await _persist();
    notifyListeners();
  }
}
