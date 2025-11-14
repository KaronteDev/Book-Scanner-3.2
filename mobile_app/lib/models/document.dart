class Document {
  final String id;
  final String title;
  final DateTime createdAt;
  final int pageCount;

  Document({
    required this.id,
    required this.title,
    required this.createdAt,
    required this.pageCount,
  });

  factory Document.fromJson(Map<String, dynamic> json) {
    return Document(
      id: json['id'] as String,
      title: json['title'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
      pageCount: json['page_count'] as int,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'created_at': createdAt.toIso8601String(),
      'page_count': pageCount,
    };
  }
}
