class ServerInfo {
  final String host;
  final int port;
  final String name;
  final String? token;

  ServerInfo({
    required this.host,
    required this.port,
    required this.name,
    this.token,
  });

  String get baseUrl => 'http://$host:$port';
  String get wsUrl => 'ws://$host:$port/sync';

  factory ServerInfo.fromJson(Map<String, dynamic> json) {
    return ServerInfo(
      host: json['host'] as String,
      port: json['port'] as int,
      name: json['name'] as String,
      token: json['token'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'host': host,
      'port': port,
      'name': name,
      'token': token,
    };
  }

  ServerInfo copyWith({String? token}) {
    return ServerInfo(
      host: host,
      port: port,
      name: name,
      token: token ?? this.token,
    );
  }
}
