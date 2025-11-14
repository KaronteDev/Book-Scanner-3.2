import 'dart:ui';

class Annotation {
  final String id;
  final String pageId;
  final String type; // 'ink', 'highlight', 'text'
  final List<Offset>? points; // for ink/highlight paths
  final Rect? rect; // for highlight/text bounding box
  final String? text; // for text notes
  final int color; // ARGB
  final double strokeWidth; // for ink/highlight
  final DateTime createdAt;
  final DateTime updatedAt;
  final String status; // 'new', 'updated', 'deleted', 'synced'

  Annotation({
    required this.id,
    required this.pageId,
    required this.type,
    this.points,
    this.rect,
    this.text,
    this.color = 0xFFFFD54F,
    this.strokeWidth = 3.0,
    required this.createdAt,
    required this.updatedAt,
    this.status = 'new',
  });

  Annotation copyWith({
    String? id,
    String? pageId,
    String? type,
    List<Offset>? points,
    Rect? rect,
    String? text,
    int? color,
    double? strokeWidth,
    DateTime? createdAt,
    DateTime? updatedAt,
    String? status,
  }) {
    return Annotation(
      id: id ?? this.id,
      pageId: pageId ?? this.pageId,
      type: type ?? this.type,
      points: points ?? this.points,
      rect: rect ?? this.rect,
      text: text ?? this.text,
      color: color ?? this.color,
      strokeWidth: strokeWidth ?? this.strokeWidth,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      status: status ?? this.status,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'page_id': pageId,
      'type': type,
      'points': points?.map((p) => {'x': p.dx, 'y': p.dy}).toList(),
      'rect': rect == null ? null : {'x': rect!.left, 'y': rect!.top, 'w': rect!.width, 'h': rect!.height},
      'text': text,
      'color': color,
      'stroke_width': strokeWidth,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
      'status': status,
    };
  }

  factory Annotation.fromJson(Map<String, dynamic> json) {
    return Annotation(
      id: json['id'] as String,
      pageId: json['page_id'] as String,
      type: json['type'] as String,
      points: (json['points'] as List?)?.map((p) => Offset((p['x'] as num).toDouble(), (p['y'] as num).toDouble())).toList(),
      rect: json['rect'] == null
          ? null
          : Rect.fromLTWH(
              (json['rect']['x'] as num).toDouble(),
              (json['rect']['y'] as num).toDouble(),
              (json['rect']['w'] as num).toDouble(),
              (json['rect']['h'] as num).toDouble(),
            ),
      text: json['text'] as String?,
      color: json['color'] as int? ?? 0xFFFFD54F,
      strokeWidth: (json['stroke_width'] as num?)?.toDouble() ?? 3.0,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      status: json['status'] as String? ?? 'synced',
    );
  }
}
