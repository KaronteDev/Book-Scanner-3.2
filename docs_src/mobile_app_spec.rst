Especificación App Móvil
========================

Objetivos
---------
- Captura desde smartphone con calidad superior a webcam.
- Sincronización directa WiFi (modo local P2P) hacia el servidor desktop.
- Revisión y corrección rápida de OCR desde tablet.
- Anotaciones táctiles (gestos: tap, long-press, pinch zoom).

Arquitectura propuesta
---------------------
- Cliente Flutter (iOS/Android) consume API REST local.
- Servidor ligero Flask en desktop expone endpoints:
  - POST /capture (sube imagen de página)
  - GET /pages/<doc_id>
  - POST /ocr/correct
  - POST /annotations
  - WS /sync (websocket para eventos en tiempo real)

Flujo de captura
----------------
1. App detecta servidor via mDNS / broadcast UDP.
2. Usuario toma foto -> compresión JPEG moderada.
3. Envío a /capture con doc_id.
4. Desktop procesa (rectificación + OCR) y emite evento WebSocket.
5. App recibe texto OCR provisional para edición.

Seguridad
---------
- Token temporal negociado al iniciar sesión local.
- Cifrado opcional (TLS) si se requiere fuera de LAN controlada.

Roadmap
-------
Fase 1: captura + subida básica.
Fase 2: vista lista páginas + corrección OCR.
Fase 3: anotaciones avanzadas + sincronización incremental.
Fase 4: modo presentación en tablet (sólo lectura + 3D remote control).
