class PageModel {
  final String id;
  final String docId;
  final int pageNumber;
  final String? imagePath;
  final String? ocrText;
  final String status; // 'pending', 'processing', 'completed'
  final DateTime createdAt;

  PageModel({
    required this.id,
    required this.docId,
    required this.pageNumber,
    this.imagePath,
    this.ocrText,
    required this.status,
    required this.createdAt,
  });

  factory PageModel.fromJson(Map<String, dynamic> json) {
    return PageModel(
      id: json['id'] as String,
      docId: json['doc_id'] as String,
      pageNumber: json['page_number'] as int,
      imagePath: json['image_path'] as String?,
      ocrText: json['ocr_text'] as String?,
      status: json['status'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'doc_id': docId,
      'page_number': pageNumber,
      'image_path': imagePath,
      'ocr_text': ocrText,
      'status': status,
      'created_at': createdAt.toIso8601String(),
    };
  }

  PageModel copyWith({
    String? id,
    String? docId,
    int? pageNumber,
    String? imagePath,
    String? ocrText,
    String? status,
    DateTime? createdAt,
  }) {
    return PageModel(
      id: id ?? this.id,
      docId: docId ?? this.docId,
      pageNumber: pageNumber ?? this.pageNumber,
      imagePath: imagePath ?? this.imagePath,
      ocrText: ocrText ?? this.ocrText,
      status: status ?? this.status,
      createdAt: createdAt ?? this.createdAt,
    );
  }
}
