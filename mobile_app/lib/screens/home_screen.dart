import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';
import '../services/websocket_service.dart';
import '../services/sync_service.dart';
import '../services/annotation_service.dart';
import '../models/annotation.dart';
import '../models/document.dart';
import 'capture_screen.dart';
import 'document_pages_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  List<Document> _documents = [];
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _loadDocuments();
    _setupWebSocketListener();
    // Start background sync
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final sync = context.read<SyncService>();
      sync.start(context);
    });
  }

  void _setupWebSocketListener() {
    final wsService = context.read<WebSocketService>();
    wsService.events.listen((event) {
      if (event['type'] == 'page_processed' || event['type'] == 'ocr_completed') {
        _loadDocuments(); // Refresh on updates
      } else if (event['type'] == 'annotation_added') {
        try {
          final annService = context.read<AnnotationService>();
          final data = Map<String, dynamic>.from(event['annotation'] ?? event);
          // Some events might send flat annotation fields
          final now = DateTime.now();
          final ann = Annotation.fromJson({
            ...data,
            'created_at': data['created_at'] ?? now.toIso8601String(),
            'updated_at': data['updated_at'] ?? now.toIso8601String(),
            'status': 'synced',
          });
          annService.add(ann, enqueue: false);
        } catch (_) {}
      }
    });
  }

  Future<void> _loadDocuments() async {
    setState(() => _isLoading = true);
    
    final apiService = context.read<ApiService>();
    final documents = await apiService.getDocuments();
    
    setState(() {
      _documents = documents;
      _isLoading = false;
    });
  }

  Future<void> _disconnect() async {
    final apiService = context.read<ApiService>();
    final wsService = context.read<WebSocketService>();
    
    await wsService.disconnect();
    await apiService.disconnect();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('GeoDocs Mobile'),
        actions: [
          Consumer<ApiService>(
            builder: (context, apiService, child) {
              return IconButton(
                icon: const Icon(Icons.info_outline),
                onPressed: () {
                  showDialog(
                    context: context,
                    builder: (context) => AlertDialog(
                      title: const Text('Server Info'),
                      content: Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Server: ${apiService.serverInfo?.name}'),
                          Text('Host: ${apiService.serverInfo?.host}:${apiService.serverInfo?.port}'),
                        ],
                      ),
                      actions: [
                        TextButton(
                          onPressed: () => Navigator.pop(context),
                          child: const Text('OK'),
                        ),
                        TextButton(
                          onPressed: () {
                            Navigator.pop(context);
                            _disconnect();
                          },
                          child: const Text('Disconnect'),
                        ),
                      ],
                    ),
                  );
                },
              );
            },
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _documents.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.folder_open, size: 64, color: Colors.grey),
                      const SizedBox(height: 16),
                      Text(
                        'No documents yet',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Tap the camera button to start capturing',
                        style: TextStyle(color: Colors.grey),
                      ),
                    ],
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _loadDocuments,
                  child: ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: _documents.length,
                    itemBuilder: (context, index) {
                      final doc = _documents[index];
                      return Card(
                        child: ListTile(
                          leading: const Icon(Icons.book),
                          title: Text(doc.title),
                          subtitle: Text('${doc.pageCount} pages'),
                          trailing: const Icon(Icons.chevron_right),
                          onTap: () {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (context) => DocumentPagesScreen(document: doc),
                              ),
                            );
                          },
                        ),
                      );
                    },
                  ),
                ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => CaptureScreen(
                documentId: _documents.isNotEmpty ? _documents.first.id : null,
              ),
            ),
          ).then((_) => _loadDocuments());
        },
        icon: const Icon(Icons.camera_alt),
        label: const Text('Capture'),
      ),
    );
  }
}
