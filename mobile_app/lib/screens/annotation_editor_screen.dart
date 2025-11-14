import 'dart:math';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/page.dart';
import '../models/annotation.dart';
import '../services/api_service.dart';
import '../services/annotation_service.dart';

class AnnotationEditorScreen extends StatefulWidget {
  final PageModel page;

  const AnnotationEditorScreen({super.key, required this.page});

  @override
  State<AnnotationEditorScreen> createState() => _AnnotationEditorScreenState();
}

class _AnnotationEditorScreenState extends State<AnnotationEditorScreen> {
  String _tool = 'ink'; // 'ink' | 'highlight' | 'text' | 'select'
  Color _color = const Color(0xFFFFD54F);
  double _strokeWidth = 4;
  final List<Offset> _currentPath = [];
  Rect? _currentRect;
  final TextEditingController _textController = TextEditingController();
  String? _selectedId;
  Offset? _lastDragPos;

  @override
  Widget build(BuildContext context) {
    final annService = context.watch<AnnotationService>();
    final api = context.read<ApiService>();

    final imageUrl = widget.page.imagePath != null
        ? widget.page.imagePath!.startsWith('/')
            ? '${api.serverInfo!.baseUrl}${widget.page.imagePath}'
            : widget.page.imagePath!
        : '';

    final anns = annService.annotationsForPage(widget.page.id);

    return Scaffold(
      appBar: AppBar(
        title: Text('Annotate p. ${widget.page.pageNumber}'),
        actions: [
          if (_selectedId != null) ...[
            IconButton(
              tooltip: 'Delete',
              icon: const Icon(Icons.delete_outline),
              onPressed: () {
                final ann = anns.firstWhere((a) => a.id == _selectedId, orElse: () => anns.first);
                context.read<AnnotationService>().delete(ann.id, ann.pageId);
                setState(() => _selectedId = null);
              },
            ),
            if (anns.any((a) => a.id == _selectedId && a.type == 'text'))
              IconButton(
                tooltip: 'Edit text',
                icon: const Icon(Icons.edit),
                onPressed: () async {
                  final ann = anns.firstWhere((a) => a.id == _selectedId);
                  _textController.text = ann.text ?? '';
                  final newText = await showDialog<String>(
                    context: context,
                    builder: (ctx) => AlertDialog(
                      title: const Text('Edit note'),
                      content: TextField(controller: _textController, autofocus: true, maxLines: 3),
                      actions: [
                        TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
                        ElevatedButton(onPressed: () => Navigator.pop(ctx, _textController.text), child: const Text('Save')),
                      ],
                    ),
                  );
                  if (newText != null) {
                    final updated = ann.copyWith(text: newText, updatedAt: DateTime.now(), status: 'updated');
                    context.read<AnnotationService>().update(updated);
                    setState(() {});
                  }
                },
              ),
          ]
        ],
      ),
      body: Column(
        children: [
          _buildToolbar(),
          Expanded(
            child: LayoutBuilder(
              builder: (context, constraints) {
                return Stack(
                  fit: StackFit.expand,
                  children: [
                    if (imageUrl.isNotEmpty)
                      Image.network(imageUrl, fit: BoxFit.contain),
                    GestureDetector(
                      onTapDown: (d) {
                        if (_tool == 'select') {
                          final id = _hitTest(anns, d.localPosition);
                          setState(() => _selectedId = id);
                        }
                      },
                      onPanStart: (d) {
                        if (_tool == 'select' && _selectedId != null) {
                          _lastDragPos = d.localPosition;
                        } else if (_tool == 'ink' || _tool == 'highlight') {
                          setState(() {
                            _currentPath.clear();
                            _currentPath.add(d.localPosition);
                          });
                        } else if (_tool == 'text') {
                          setState(() {
                            _currentRect = Rect.fromLTWH(d.localPosition.dx, d.localPosition.dy, 160, 60);
                          });
                        }
                      },
                      onPanUpdate: (d) {
                        if (_tool == 'select' && _selectedId != null && _lastDragPos != null) {
                          final delta = d.localPosition - _lastDragPos!;
                          _lastDragPos = d.localPosition;
                          final svc = context.read<AnnotationService>();
                          final ann = anns.firstWhere((a) => a.id == _selectedId);
                          if (ann.rect != null) {
                            svc.update(ann.copyWith(
                              rect: ann.rect!.shift(delta),
                              updatedAt: DateTime.now(),
                              status: 'updated',
                            ));
                          } else if (ann.points != null) {
                            final moved = ann.points!.map((p) => p + delta).toList();
                            svc.update(ann.copyWith(
                              points: moved,
                              updatedAt: DateTime.now(),
                              status: 'updated',
                            ));
                          }
                        } else if (_tool == 'ink' || _tool == 'highlight') {
                          setState(() {
                            _currentPath.add(d.localPosition);
                          });
                        } else if (_tool == 'text' && _currentRect != null) {
                          setState(() {
                            final r = _currentRect!;
                            _currentRect = Rect.fromLTWH(min(r.left, d.localPosition.dx), min(r.top, d.localPosition.dy),
                                (d.localPosition.dx - r.left).abs(), (d.localPosition.dy - r.top).abs());
                          });
                        }
                      },
                      onPanEnd: (_) {
                        final id = UniqueKey().toString();
                        final now = DateTime.now();
                        if (_tool == 'select') {
                          _lastDragPos = null;
                        } else if ((_tool == 'ink' || _tool == 'highlight') && _currentPath.isNotEmpty) {
                          annService.add(Annotation(
                            id: id,
                            pageId: widget.page.id,
                            type: _tool,
                            points: List.of(_currentPath),
                            rect: null,
                            text: null,
                            color: _color.value,
                            strokeWidth: _strokeWidth,
                            createdAt: now,
                            updatedAt: now,
                            status: 'new',
                          ));
                          setState(() => _currentPath.clear());
                        } else if (_tool == 'text' && _currentRect != null) {
                          _showTextDialog().then((text) {
                            if (text != null && text.isNotEmpty) {
                              annService.add(Annotation(
                                id: id,
                                pageId: widget.page.id,
                                type: 'text',
                                points: null,
                                rect: _currentRect,
                                text: text,
                                color: _color.value,
                                strokeWidth: 1.5,
                                createdAt: now,
                                updatedAt: now,
                                status: 'new',
                              ));
                            }
                            setState(() => _currentRect = null);
                          });
                        }
                      },
                      child: CustomPaint(
                        painter: _AnnotationPainter(
                          annotations: anns,
                          currentPath: _currentPath,
                          currentRect: _currentRect,
                          currentColor: _color,
                          currentStroke: _strokeWidth,
                          currentTool: _tool,
                          selectedId: _selectedId,
                        ),
                      ),
                    ),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildToolbar() {
    return Container(
      color: Colors.grey.shade100,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Row(
        children: [
          ToggleButtons(
            isSelected: ['ink', 'highlight', 'text', 'select'].map((t) => t == _tool).toList(),
            onPressed: (i) {
              setState(() => _tool = ['ink', 'highlight', 'text', 'select'][i]);
            },
            children: const [
              Padding(padding: EdgeInsets.all(8), child: Icon(Icons.gesture)),
              Padding(padding: EdgeInsets.all(8), child: Icon(Icons.border_color)),
              Padding(padding: EdgeInsets.all(8), child: Icon(Icons.text_fields)),
              Padding(padding: EdgeInsets.all(8), child: Icon(Icons.near_me)),
            ],
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Slider(
              min: 1,
              max: 12,
              value: _strokeWidth,
              label: 'Stroke: ${_strokeWidth.toStringAsFixed(0)}',
              onChanged: (v) {
                setState(() => _strokeWidth = v);
                if (_selectedId != null) {
                  final svc = context.read<AnnotationService>();
                  final anns = svc.annotationsForPage(widget.page.id);
                  final ann = anns.firstWhere((a) => a.id == _selectedId, orElse: () => anns.first);
                  if (ann.type != 'text') {
                    svc.update(ann.copyWith(strokeWidth: v, updatedAt: DateTime.now(), status: 'updated'));
                  }
                }
              },
            ),
          ),
          IconButton(
            icon: const Icon(Icons.color_lens),
            onPressed: () async {
              final c = await showDialog<Color>(
                context: context,
                builder: (ctx) => AlertDialog(
                  title: const Text('Pick color'),
                  content: Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      0xFFFFD54F, 0x80FFF59D, 0x80FF8A80, 0x8090CAF9, 0x80CE93D8, 0x80A5D6A7
                    ].map((hex) {
                      return GestureDetector(
                        onTap: () => Navigator.pop(ctx, Color(hex)),
                        child: Container(width: 28, height: 28, decoration: BoxDecoration(color: Color(hex), shape: BoxShape.circle)),
                      );
                    }).toList(),
                  ),
                  actions: [TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel'))],
                ),
              );
              if (c != null) {
                setState(() => _color = c);
                if (_selectedId != null) {
                  final svc = context.read<AnnotationService>();
                  final anns = svc.annotationsForPage(widget.page.id);
                  final ann = anns.firstWhere((a) => a.id == _selectedId, orElse: () => anns.first);
                  svc.update(ann.copyWith(color: c.value, updatedAt: DateTime.now(), status: 'updated'));
                }
              }
            },
          ),
        ],
      ),
    );
  }

  Future<String?> _showTextDialog() async {
    _textController.clear();
    return showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Add note'),
        content: TextField(controller: _textController, autofocus: true, maxLines: 3),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          ElevatedButton(onPressed: () => Navigator.pop(ctx, _textController.text), child: const Text('Add')),
        ],
      ),
    );
  }
}

class _AnnotationPainter extends CustomPainter {
  final List<Annotation> annotations;
  final List<Offset> currentPath;
  final Rect? currentRect;
  final Color currentColor;
  final double currentStroke;
  final String currentTool;
  final String? selectedId;

  _AnnotationPainter({
    required this.annotations,
    required this.currentPath,
    required this.currentRect,
    required this.currentColor,
    required this.currentStroke,
    required this.currentTool,
    required this.selectedId,
  });

  @override
  void paint(Canvas canvas, Size size) {
    // Draw existing annotations
    for (final a in annotations) {
      if (a.type == 'ink' && a.points != null && a.points!.isNotEmpty) {
        final p = Paint()
          ..color = Color(a.color)
          ..strokeWidth = a.strokeWidth
          ..style = PaintingStyle.stroke
          ..strokeCap = StrokeCap.round
          ..strokeJoin = StrokeJoin.round;
        final path = Path()..moveTo(a.points!.first.dx, a.points!.first.dy);
        for (int i = 1; i < a.points!.length; i++) {
          path.lineTo(a.points![i].dx, a.points![i].dy);
        }
        canvas.drawPath(path, p);
        if (a.id == selectedId) {
          final sel = Paint()
            ..color = Colors.blueAccent
            ..style = PaintingStyle.stroke
            ..strokeWidth = 1
            ..pathEffect = null;
          final rect = _pointsBounds(a.points!);
          canvas.drawRRect(RRect.fromRectAndRadius(rect.inflate(6), const Radius.circular(4)), sel);
        }
      } else if (a.type == 'highlight' && a.points != null && a.points!.isNotEmpty) {
        final p = Paint()
          ..color = Color(a.color)
          ..strokeWidth = a.strokeWidth
          ..style = PaintingStyle.stroke
          ..strokeCap = StrokeCap.round
          ..strokeJoin = StrokeJoin.round
          ..blendMode = BlendMode.multiply;
        final path = Path()..moveTo(a.points!.first.dx, a.points!.first.dy);
        for (int i = 1; i < a.points!.length; i++) {
          path.lineTo(a.points![i].dx, a.points![i].dy);
        }
        canvas.drawPath(path, p);
        if (a.id == selectedId) {
          final rect = _pointsBounds(a.points!);
          final sel = Paint()
            ..color = Colors.blueAccent
            ..style = PaintingStyle.stroke
            ..strokeWidth = 1;
          canvas.drawRRect(RRect.fromRectAndRadius(rect.inflate(6), const Radius.circular(4)), sel);
        }
      } else if (a.type == 'text' && a.rect != null && a.text != null) {
        final r = a.rect!;
        final bg = Paint()..color = Color(a.color).withOpacity(0.25);
        canvas.drawRRect(RRect.fromRectAndRadius(r, const Radius.circular(4)), bg);
        final tp = TextPainter(text: TextSpan(text: a.text, style: const TextStyle(color: Colors.black)), textDirection: TextDirection.ltr);
        tp.layout(maxWidth: r.width - 8);
        tp.paint(canvas, Offset(r.left + 4, r.top + 4));
        if (a.id == selectedId) {
          final sel = Paint()
            ..color = Colors.blueAccent
            ..style = PaintingStyle.stroke
            ..strokeWidth = 1.5;
          canvas.drawRRect(RRect.fromRectAndRadius(r.inflate(3), const Radius.circular(4)), sel);
        }
      }
    }

    // Draw current gesture
    if (currentTool == 'ink' || currentTool == 'highlight') {
      if (currentPath.isNotEmpty) {
        final p = Paint()
          ..color = currentColor
          ..strokeWidth = currentStroke
          ..style = PaintingStyle.stroke
          ..strokeCap = StrokeCap.round
          ..strokeJoin = StrokeJoin.round
          ..blendMode = currentTool == 'highlight' ? BlendMode.multiply : BlendMode.srcOver;
        final path = Path()..moveTo(currentPath.first.dx, currentPath.first.dy);
        for (int i = 1; i < currentPath.length; i++) {
          path.lineTo(currentPath[i].dx, currentPath[i].dy);
        }
        canvas.drawPath(path, p);
      }
    } else if (currentTool == 'text' && currentRect != null) {
      final r = currentRect!;
      final p = Paint()
        ..color = currentColor.withOpacity(0.25)
        ..style = PaintingStyle.fill;
      canvas.drawRRect(RRect.fromRectAndRadius(r, const Radius.circular(4)), p);
    }
  }

  @override
  bool shouldRepaint(covariant _AnnotationPainter oldDelegate) => true;

  Rect _pointsBounds(List<Offset> pts) {
    double minX = pts.first.dx, minY = pts.first.dy, maxX = pts.first.dx, maxY = pts.first.dy;
    for (final p in pts) {
      if (p.dx < minX) minX = p.dx;
      if (p.dy < minY) minY = p.dy;
      if (p.dx > maxX) maxX = p.dx;
      if (p.dy > maxY) maxY = p.dy;
    }
    return Rect.fromLTRB(minX, minY, maxX, maxY);
  }
}

extension on _AnnotationEditorScreenState {
  String? _hitTest(List<Annotation> anns, Offset pos) {
    const padding = 10.0;
    for (final a in anns.reversed) {
      if (a.rect != null) {
        if (a.rect!.inflate(padding).contains(pos)) return a.id;
      } else if (a.points != null && a.points!.isNotEmpty) {
        final rect = _pointsBounds(a.points!);
        if (rect.inflate(padding).contains(pos)) return a.id;
      }
    }
    return null;
  }

  Rect _pointsBounds(List<Offset> pts) {
    double minX = pts.first.dx, minY = pts.first.dy, maxX = pts.first.dx, maxY = pts.first.dy;
    for (final p in pts) {
      if (p.dx < minX) minX = p.dx;
      if (p.dy < minY) minY = p.dy;
      if (p.dx > maxX) maxX = p.dx;
      if (p.dy > maxY) maxY = p.dy;
    }
    return Rect.fromLTRB(minX, minY, maxX, maxY);
  }
}
