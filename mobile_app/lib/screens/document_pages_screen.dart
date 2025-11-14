import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/document.dart';
import '../models/page.dart';
import '../services/api_service.dart';
import 'ocr_correction_screen.dart';
import 'annotation_editor_screen.dart';

class DocumentPagesScreen extends StatefulWidget {
  final Document document;

  const DocumentPagesScreen({super.key, required this.document});

  @override
  State<DocumentPagesScreen> createState() => _DocumentPagesScreenState();
}

class _DocumentPagesScreenState extends State<DocumentPagesScreen> {
  List<PageModel> _pages = [];
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _loadPages();
  }

  Future<void> _loadPages() async {
    setState(() => _isLoading = true);
    
    final apiService = context.read<ApiService>();
    final pages = await apiService.getPages(widget.document.id);
    
    setState(() {
      _pages = pages;
      _isLoading = false;
    });
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'completed':
        return Colors.green;
      case 'processing':
        return Colors.orange;
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.document.title),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _pages.isEmpty
              ? const Center(
                  child: Text('No pages yet'),
                )
              : RefreshIndicator(
                  onRefresh: _loadPages,
                  child: ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: _pages.length,
                    itemBuilder: (context, index) {
                      final page = _pages[index];
                      return Card(
                        child: ListTile(
                          leading: CircleAvatar(
                            backgroundColor: _getStatusColor(page.status),
                            child: Text(
                              '${page.pageNumber}',
                              style: const TextStyle(color: Colors.white),
                            ),
                          ),
                          title: Text('Page ${page.pageNumber}'),
                          subtitle: Text(
                            page.status == 'completed' 
                                ? 'OCR completed'
                                : page.status == 'processing'
                                    ? 'Processing...'
                                    : 'Pending',
                          ),
                          trailing: page.status == 'completed'
                              ? Wrap(spacing: 8, children: const [Icon(Icons.edit), Icon(Icons.brush)])
                              : null,
                          onTap: page.status == 'completed'
                              ? () {
                                  showModalBottomSheet(
                                    context: context,
                                    builder: (_) => SafeArea(
                                      child: Wrap(children: [
                                        ListTile(
                                          leading: const Icon(Icons.edit),
                                          title: const Text('Edit OCR text'),
                                          onTap: () {
                                            Navigator.pop(context);
                                            Navigator.push(
                                              context,
                                              MaterialPageRoute(
                                                builder: (context) => OcrCorrectionScreen(page: page),
                                              ),
                                            ).then((_) => _loadPages());
                                          },
                                        ),
                                        ListTile(
                                          leading: const Icon(Icons.brush),
                                          title: const Text('Annotate page'),
                                          onTap: () {
                                            Navigator.pop(context);
                                            Navigator.push(
                                              context,
                                              MaterialPageRoute(
                                                builder: (context) => AnnotationEditorScreen(page: page),
                                              ),
                                            );
                                          },
                                        ),
                                      ]),
                                    ),
                                  );
                                }
                              : null,
                        ),
                      );
                    },
                  ),
                ),
    );
  }
}
