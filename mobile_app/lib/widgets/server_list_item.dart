import 'package:flutter/material.dart';
import '../models/server_info.dart';

class ServerListItem extends StatelessWidget {
  final ServerInfo server;
  final VoidCallback onTap;

  const ServerListItem({
    super.key,
    required this.server,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: const Icon(Icons.computer, size: 40),
        title: Text(server.name),
        subtitle: Text('${server.host}:${server.port}'),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}
