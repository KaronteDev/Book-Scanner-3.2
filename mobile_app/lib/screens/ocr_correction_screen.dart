import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/page.dart';
import '../services/api_service.dart';

class OcrCorrectionScreen extends StatefulWidget {
  final PageModel page;

  const OcrCorrectionScreen({super.key, required this.page});

  @override
  State<OcrCorrectionScreen> createState() => _OcrCorrectionScreenState();
}

class _OcrCorrectionScreenState extends State<OcrCorrectionScreen> {
  late TextEditingController _textController;
  bool _hasChanges = false;
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _textController = TextEditingController(text: widget.page.ocrText ?? '');
    _textController.addListener(() {
      setState(() {
        _hasChanges = _textController.text != widget.page.ocrText;
      });
    });
  }

  Future<void> _saveCorrections() async {
    setState(() => _isSaving = true);

    final apiService = context.read<ApiService>();
    final success = await apiService.correctOcr(
      widget.page.id,
      _textController.text,
    );

    setState(() => _isSaving = false);

    if (mounted) {
      if (success) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Corrections saved')),
        );
        Navigator.pop(context);
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to save corrections')),
        );
      }
    }
  }

  @override
  void dispose() {
    _textController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Page ${widget.page.pageNumber}'),
        actions: [
          if (_hasChanges)
            IconButton(
              icon: _isSaving
                  ? const SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Icon(Icons.save),
              onPressed: _isSaving ? null : _saveCorrections,
            ),
        ],
      ),
      body: Column(
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            color: Colors.blue.shade50,
            child: Row(
              children: [
                const Icon(Icons.info_outline, color: Colors.blue),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Edit the OCR text below to correct any errors',
                    style: TextStyle(color: Colors.blue.shade900),
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: TextField(
                controller: _textController,
                maxLines: null,
                expands: true,
                textAlignVertical: TextAlignVertical.top,
                decoration: const InputDecoration(
                  hintText: 'OCR text will appear here...',
                  border: OutlineInputBorder(),
                ),
              ),
            ),
          ),
          if (_hasChanges)
            Container(
              padding: const EdgeInsets.all(16),
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: _isSaving ? null : _saveCorrections,
                icon: const Icon(Icons.save),
                label: const Text('Save Corrections'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.all(16),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
