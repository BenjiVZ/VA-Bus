import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/status.dart' as ws_status;

import '../config/constants.dart';

/// Evento recibido del servidor cuando cambia el estado de un asiento.
class SeatChangedEvent {
  /// 'locked' | 'unlocked' | 'reserved' | 'released'
  final String estado;
  final int numero;
  final int piso;
  final int? usuarioId;

  SeatChangedEvent({
    required this.estado,
    required this.numero,
    required this.piso,
    this.usuarioId,
  });

  factory SeatChangedEvent.fromJson(Map<String, dynamic> j) => SeatChangedEvent(
        estado: (j['estado'] ?? '') as String,
        numero: (j['numero'] ?? 0) as int,
        piso: (j['piso'] ?? 1) as int,
        usuarioId: j['usuario_id'] as int?,
      );
}

/// Cliente WebSocket que escucha cambios de asientos para un viaje específico.
///
/// Reconecta automáticamente con backoff exponencial. Expone los eventos
/// como un `Stream<SeatChangedEvent>` y permite cerrar limpiamente.
///
///   final ws = AsientosWs(viajeId: 826);
///   ws.events.listen((evt) { ... });
///   ws.connect();
///   ...
///   ws.dispose();
class AsientosWs {
  final String viajeId;
  final _controller = StreamController<SeatChangedEvent>.broadcast();

  WebSocketChannel? _channel;
  StreamSubscription? _sub;
  Timer? _reconnectTimer;
  int _attempts = 0;
  bool _closed = false;

  AsientosWs({required this.viajeId});

  Stream<SeatChangedEvent> get events => _controller.stream;

  String get _wsUrl {
    // Convertir el baseUrl HTTP(s) a WS(s) y quitar /api.
    var base = AppConfig.apiOrigin;
    if (base.startsWith('https://')) {
      base = 'wss://${base.substring(8)}';
    } else if (base.startsWith('http://')) {
      base = 'ws://${base.substring(7)}';
    }
    return '$base/ws/viajes/$viajeId/asientos/';
  }

  void connect() {
    if (_closed) return;
    _disconnectInternal();

    try {
      final ch = WebSocketChannel.connect(Uri.parse(_wsUrl));
      _channel = ch;
      _sub = ch.stream.listen(
        _onData,
        onError: (_) => _scheduleReconnect(),
        onDone: _scheduleReconnect,
        cancelOnError: true,
      );
      _attempts = 0;
    } catch (_) {
      _scheduleReconnect();
    }
  }

  void _onData(dynamic raw) {
    try {
      final str = raw is String ? raw : (raw is List<int> ? utf8.decode(raw) : '');
      if (str.isEmpty) return;
      final data = jsonDecode(str);
      if (data is! Map<String, dynamic>) return;
      if (data['type'] != 'seat_changed') return;
      _controller.add(SeatChangedEvent.fromJson(data));
    } catch (_) {/* mensaje malformado: ignorar */}
  }

  void _scheduleReconnect() {
    if (_closed) return;
    final delaySec = (1 << _attempts).clamp(1, 30);
    _attempts += 1;
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(Duration(seconds: delaySec), connect);
  }

  void _disconnectInternal() {
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
    _sub?.cancel();
    _sub = null;
    try {
      _channel?.sink.close(ws_status.goingAway);
    } catch (_) {}
    _channel = null;
  }

  Future<void> dispose() async {
    _closed = true;
    _disconnectInternal();
    await _controller.close();
  }
}
