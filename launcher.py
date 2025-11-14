
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess, sys, signal, time, threading, re
from datetime import datetime
from pathlib import Path
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, scrolledtext
except Exception as ex:
    print("Tkinter requerido:", ex); sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent
server_proc = None
log_thread = None
log_stop_event = None
log_file_handle = None
log_file_path = None

def _server_running():
    global server_proc
    return server_proc is not None and server_proc.poll() is None

def start_mobile_server(status_label=None, toggle_btn=None, logs_btn=None, with_logs=False, log_widget=None, env_extra=None):
    """Start Flask-SocketIO mobile API server (start_mobile_server.py)"""
    global server_proc
    if _server_running():
        return
    try:
        creation = 0
        if sys.platform.startswith('win'):
            # Create its own process group so we can send CTRL_BREAK_EVENT on stop
            creation |= subprocess.CREATE_NEW_PROCESS_GROUP
            if with_logs:
                # Spawn with a new console window to show logs
                creation |= subprocess.CREATE_NEW_CONSOLE
        cmd = [sys.executable]
        if log_widget is not None:
            cmd.append('-u')  # unbuffered for real-time stdout
        cmd.append(str(BASE_DIR/"start_mobile_server.py"))
        # Build environment
        env = None
        if env_extra is not None:
            try:
                import os as _os
                env = _os.environ.copy()
                env.update(env_extra)
            except Exception:
                env = None
        server_proc = subprocess.Popen(
            cmd,
            cwd=str(BASE_DIR),
            stdout=(subprocess.PIPE if log_widget is not None else (None if with_logs else subprocess.DEVNULL)),
            stderr=(subprocess.STDOUT if log_widget is not None else (None if with_logs else subprocess.STDOUT)),
            creationflags=creation,
            bufsize=1,
            universal_newlines=True,
            env=env,
        )
        if status_label:
            status_label.config(text="Servidor móvil: ejecutándose en puerto 5000")
        if toggle_btn:
            toggle_btn.config(text="⏹ Detener Servidor Móvil")
        if logs_btn:
            logs_btn.state(["disabled"])  # disable while running
        # Start log reader if widget provided
        if log_widget is not None and server_proc.stdout:
            _start_log_reader(server_proc, log_widget)
    except Exception as e:
        if status_label:
            status_label.config(text=f"Error al iniciar servidor: {e}")

def stop_mobile_server(status_label=None, toggle_btn=None, logs_btn=None):
    """Stop the mobile API server if running"""
    global server_proc
    if not _server_running():
        return
    try:
        # Stop log reader first
        _stop_log_reader()
        if sys.platform.startswith('win'):
            # Send CTRL-BREAK to the process group if possible; fallback to terminate
            try:
                server_proc.send_signal(signal.CTRL_BREAK_EVENT)
            except Exception:
                server_proc.terminate()
        else:
            server_proc.terminate()
        # Wait briefly, then force kill if needed
        for _ in range(20):
            if server_proc.poll() is not None:
                break
            time.sleep(0.1)
        if server_proc.poll() is None:
            server_proc.kill()
    finally:
        server_proc = None
        if status_label:
            status_label.config(text="Servidor móvil: detenido")
        if toggle_btn:
            toggle_btn.config(text="📶 Iniciar Servidor Móvil")
        if logs_btn:
            logs_btn.state(["!disabled"])  # re-enable


def _start_log_reader(proc, widget):
    """Read process stdout lines and append to the Tk widget safely"""
    global log_thread, log_stop_event, log_file_handle, log_file_path
    log_stop_event = threading.Event()

    # Prepare persistent log file
    logs_dir = BASE_DIR / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d-%H%M%S')
    log_file_path = logs_dir / f'mobile_server_{ts}.log'
    try:
        log_file_handle = open(log_file_path, 'a', encoding='utf-8', buffering=1)
    except Exception:
        log_file_handle = None

    def _classify_level(text: str) -> str:
        t = text.strip()
        if re.search(r"\bERROR\b|\bCRITICAL\b|\[?ERROR\]?|\[?CRITICAL\]?", t, re.IGNORECASE):
            return 'level-error'
        if re.search(r"\bWARNING\b|\bWARN\b|\[?WARN(ING)?\]?", t, re.IGNORECASE):
            return 'level-warn'
        if re.search(r"\bINFO\b|\[?INFO\]?", t, re.IGNORECASE):
            return 'level-info'
        if re.search(r"\bDEBUG\b|\[?DEBUG\]?", t, re.IGNORECASE):
            return 'level-debug'
        return 'level-plain'

    def append(text: str):
        try:
            widget.insert('end', text, _classify_level(text))
            widget.see('end')
        except Exception:
            pass

    def reader():
        try:
            while not log_stop_event.is_set():
                line = proc.stdout.readline()
                if not line:
                    break
                # Persist to file
                try:
                    if log_file_handle is not None:
                        log_file_handle.write(line)
                except Exception:
                    pass
                widget.after(0, append, line)
        except Exception:
            pass

    log_thread = threading.Thread(target=reader, daemon=True)
    log_thread.start()


def _stop_log_reader():
    global log_thread, log_stop_event, log_file_handle
    if log_stop_event is not None:
        log_stop_event.set()
    if log_thread is not None:
        try:
            log_thread.join(timeout=1.0)
        except Exception:
            pass
    log_thread = None
    log_stop_event = None
    # Close log file if open
    try:
        if log_file_handle is not None:
            log_file_handle.close()
    except Exception:
        pass
    log_file_handle = None

def launch_scanner():
    subprocess.Popen([sys.executable, str(BASE_DIR/"scanner_gui.py")])

def launch_annotator():
    subprocess.Popen([sys.executable, str(BASE_DIR/"annotator_gui.py")])

def main():
    # Chequeo de entorno previo
    try:
        from utils.env_check import check_environment
        rep = check_environment()
        if not rep.ok:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk(); root.withdraw()
            msg = "\n".join(rep.issues)
            messagebox.showwarning("Entorno incompleto", f"Algunas dependencias opcionales faltan:\n{msg}")
    except Exception as e:
        print("[WARN] Fallo chequeo entorno:", e)
    root = tk.Tk()
    root.title("GeoDocs Scanner v23 — Selector")
    root.geometry("480x240")
    frm = ttk.Frame(root, padding=20)
    frm.pack(fill="both", expand=True)
    ttk.Label(frm, text="GeoDocs Research Suite", font=("TkDefaultFont", 14, "bold")).pack(pady=8)
    ttk.Label(frm, text="Elige un módulo:").pack(pady=6)
    row = ttk.Frame(frm); row.pack(pady=12)
    ttk.Button(row, text="🎥 Escanear (cámara)", width=24, command=launch_scanner).pack(side="left", padx=10)
    ttk.Button(row, text="📝 Anotar / Exportar", width=24, command=launch_annotator).pack(side="left", padx=10)
    # Mobile server controls
    sep = ttk.Separator(frm, orient='horizontal'); sep.pack(fill='x', pady=10)
    status = ttk.Label(frm, text="Servidor móvil: detenido")
    status.pack()
    btn_frame = ttk.Frame(frm); btn_frame.pack(pady=6)
    def toggle_server():
        if _server_running():
            stop_mobile_server(status, toggle_btn, logs_btn)
        else:
            env_extra = {"GEODOCS_LOG_LEVEL": log_level_var.get()}
            start_mobile_server(status, toggle_btn, logs_btn, with_logs=False, log_widget=log_box, env_extra=env_extra)
    toggle_btn = ttk.Button(btn_frame, text="📶 Iniciar Servidor Móvil", width=30, command=toggle_server)
    toggle_btn.pack(side="left", padx=6)

    # Console mode colorization toggle and log level selector
    console_colorize_var = tk.BooleanVar(value=True)
    log_level_var = tk.StringVar(value="INFO")
    
    def run_with_logs():
        if not _server_running():
            env_extra = {}
            if console_colorize_var.get():
                env_extra["GEODOCS_COLOR_LOGS"] = "1"
            env_extra["GEODOCS_LOG_LEVEL"] = log_level_var.get()
            start_mobile_server(status, toggle_btn, logs_btn, with_logs=True, env_extra=env_extra)
    logs_btn = ttk.Button(btn_frame, text="📡 Iniciar con logs (consola)", width=30, command=run_with_logs)
    logs_btn.pack(side="left", padx=6)
    
    opts_row = ttk.Frame(frm); opts_row.pack(fill='x', pady=(0, 6))
    ttk.Checkbutton(opts_row, text="Colorizar modo consola", variable=console_colorize_var).pack(side='left', padx=(0, 10))
    ttk.Label(opts_row, text="Nivel de log:").pack(side='left', padx=(10, 4))
    log_level_combo = ttk.Combobox(opts_row, textvariable=log_level_var, values=["DEBUG", "INFO", "WARNING", "ERROR"], state="readonly", width=10)
    log_level_combo.pack(side='left')

    # Embedded log panel
    ttk.Label(frm, text="Logs del servidor móvil (embebidos)").pack(pady=(8, 2))
    log_box = scrolledtext.ScrolledText(frm, height=12, wrap='word')
    log_box.configure(font=("Consolas", 9))
    # Color tags for log levels
    log_box.tag_configure('level-plain', foreground='#222222')
    log_box.tag_configure('level-info', foreground='#0b5394')   # blue
    log_box.tag_configure('level-warn', foreground='#b45f06')   # orange/brown
    log_box.tag_configure('level-error', foreground='#cc0000')  # red
    log_box.tag_configure('level-debug', foreground='#6e7681')  # gray
    log_box.pack(fill='both', expand=True)
    clear_row = ttk.Frame(frm); clear_row.pack(fill='x', pady=(4, 2))
    def clear_logs():
        log_box.delete('1.0', 'end')
    def open_logs_folder():
        try:
            logs_dir = BASE_DIR / 'logs'
            logs_dir.mkdir(parents=True, exist_ok=True)
            if sys.platform.startswith('win'):
                import os as _os
                _os.startfile(str(logs_dir))
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', str(logs_dir)])
            else:
                subprocess.Popen(['xdg-open', str(logs_dir)])
        except Exception:
            pass
    ttk.Button(clear_row, text="Abrir carpeta de logs", command=open_logs_folder).pack(side='left')
    ttk.Button(clear_row, text="Limpiar logs", command=clear_logs).pack(side='right')

    ttk.Label(frm, text="Sugerencia: usa 'Escanear' solo cuando vayas a capturar.\nPara describir, anotar o exportar, usa 'Anotar / Exportar'.", justify="center").pack(pady=10)
    root.mainloop()

if __name__ == "__main__":
    main()
