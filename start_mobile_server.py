"""
Script to start the mobile API server with mDNS discovery
"""

import sys, os, logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from services.mobile_api_server import app, socketio, start_mdns_service, SERVICE_PORT

COLOR_CONSOLE = os.getenv('GEODOCS_COLOR_LOGS') == '1'

ANSI = {
    'reset': '\033[0m',
    'red': '\033[31m',
    'yellow': '\033[33m',
    'blue': '\033[34m',
    'gray': '\033[90m',
}

def _c(text, color):
    if not COLOR_CONSOLE:
        return text
    return f"{ANSI.get(color,'')}{text}{ANSI['reset']}"

class _ColorFormatter(logging.Formatter):
    COLORS = {
        'CRITICAL': 'red',
        'ERROR': 'red',
        'WARNING': 'yellow',
        'INFO': 'blue',
        'DEBUG': 'gray',
    }
    def format(self, record):
        msg = super().format(record)
        color = self.COLORS.get(record.levelname, None)
        return _c(msg, color) if color else msg

def _setup_colored_logging():
    if not COLOR_CONSOLE:
        return
    try:
        # Get log level from env or default to INFO
        level_name = os.getenv('GEODOCS_LOG_LEVEL', 'INFO').upper()
        level = getattr(logging, level_name, logging.INFO)
        
        handler = logging.StreamHandler(sys.stdout)
        fmt = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        handler.setFormatter(_ColorFormatter(fmt))
        root = logging.getLogger()
        root.handlers.clear()
        root.addHandler(handler)
        root.setLevel(level)
        for name in ('werkzeug', 'engineio', 'socketio'):
            lg = logging.getLogger(name)
            lg.setLevel(level)
            lg.propagate = True
    except Exception:
        pass

if __name__ == '__main__':
    _setup_colored_logging()
    print(_c("=" * 60, 'blue'))
    print(_c("GeoDocs Scanner - Mobile API Server", 'blue'))
    print(_c("=" * 60, 'blue'))
    print()
    
    # Start mDNS service
    zeroconf = start_mdns_service()
    
    print()
    print(_c("Mobile devices can now discover this server automatically", 'blue'))
    print(_c("Or connect manually to: http://[your-ip]:5000", 'blue'))
    print()
    print(_c("Press Ctrl+C to stop the server", 'yellow'))
    print()
    
    try:
        # Run Flask-SocketIO server
        socketio.run(app, host='0.0.0.0', port=SERVICE_PORT, debug=False)
    except KeyboardInterrupt:
        print(_c("\nShutting down...", 'yellow'))
    finally:
        if zeroconf:
            print(_c("Unregistering mDNS service...", 'yellow'))
            zeroconf.unregister_all_services()
            zeroconf.close()
        print(_c("Server stopped", 'red'))
