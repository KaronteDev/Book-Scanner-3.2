import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'services/server_discovery_service.dart';
import 'services/api_service.dart';
import 'services/websocket_service.dart';
import 'screens/home_screen.dart';
import 'screens/server_discovery_screen.dart';
import 'services/annotation_service.dart';
import 'services/sync_service.dart';

void main() {
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ServerDiscoveryService()),
        ChangeNotifierProvider(create: (_) => ApiService()),
        ChangeNotifierProvider(create: (_) => WebSocketService()),
        ChangeNotifierProvider(create: (_) => AnnotationService()..load()),
        ChangeNotifierProvider(create: (_) => SyncService()),
      ],
      child: const GeoDocsMobileApp(),
    ),
  );
}

class GeoDocsMobileApp extends StatelessWidget {
  const GeoDocsMobileApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'GeoDocs Mobile',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      home: Consumer<ApiService>(
        builder: (context, apiService, child) {
          if (apiService.isConnected) {
            return const HomeScreen();
          }
          return const ServerDiscoveryScreen();
        },
      ),
    );
  }
}
