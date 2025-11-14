import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/server_discovery_service.dart';
import '../services/api_service.dart';
import '../services/websocket_service.dart';
import '../models/server_info.dart';
import '../widgets/server_list_item.dart';

class ServerDiscoveryScreen extends StatefulWidget {
  const ServerDiscoveryScreen({super.key});

  @override
  State<ServerDiscoveryScreen> createState() => _ServerDiscoveryScreenState();
}

class _ServerDiscoveryScreenState extends State<ServerDiscoveryScreen> {
  bool _isConnecting = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<ServerDiscoveryService>().startDiscovery();
    });
  }

  @override
  void dispose() {
    context.read<ServerDiscoveryService>().stopDiscovery();
    super.dispose();
  }

  Future<void> _connectToServer(ServerInfo server) async {
    setState(() => _isConnecting = true);

    final apiService = context.read<ApiService>();
    final wsService = context.read<WebSocketService>();

    final success = await apiService.connect(server);

    if (success && mounted) {
      await wsService.connect(server);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Connected to ${server.name}')),
        );
      }
    } else if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Failed to connect')),
      );
    }

    setState(() => _isConnecting = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Find Server'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              context.read<ServerDiscoveryService>()
                ..stopDiscovery()
                ..startDiscovery();
            },
          ),
        ],
      ),
      body: Consumer<ServerDiscoveryService>(
        builder: (context, discoveryService, child) {
          if (_isConnecting) {
            return const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 16),
                  Text('Connecting...'),
                ],
              ),
            );
          }

          if (discoveryService.servers.isEmpty) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.search, size: 64, color: Colors.grey),
                  const SizedBox(height: 16),
                  Text(
                    discoveryService.isDiscovering
                        ? 'Searching for servers...'
                        : 'No servers found',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Make sure GeoDocs Scanner is running\non your computer',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.grey),
                  ),
                ],
              ),
            );
          }

          return ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: discoveryService.servers.length,
            itemBuilder: (context, index) {
              final server = discoveryService.servers[index];
              return ServerListItem(
                server: server,
                onTap: () => _connectToServer(server),
              );
            },
          );
        },
      ),
    );
  }
}
