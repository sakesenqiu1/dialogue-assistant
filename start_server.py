"""Find a free port and start the app. Exits when the console window is closed."""
import atexit
import os
import signal
import socket
import sys
from pathlib import Path

PORTS = (8000, 8001, 8765, 8877)
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
PID_FILE = DATA / "server.pid"
PORT_FILE = DATA / "server.port"


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def _write_runtime(port: int) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    PORT_FILE.write_text(str(port), encoding="utf-8")


def _cleanup_runtime() -> None:
    for f in (PID_FILE, PORT_FILE):
        try:
            f.unlink(missing_ok=True)
        except OSError:
            pass


def _install_windows_console_handler() -> None:
    if sys.platform != "win32":
        return
    import ctypes

    kernel32 = ctypes.windll.kernel32
    HandlerRoutine = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)

    def _handler(event: int) -> bool:
        # CTRL_CLOSE_EVENT=2: user closed the console window
        if event in (0, 1, 2, 5, 6):
            _cleanup_runtime()
            os._exit(0)
        return False

    kernel32.SetConsoleCtrlHandler(HandlerRoutine(_handler), True)


def main() -> None:
    port = None
    for p in PORTS:
        if port_free(p):
            port = p
            break
    if port is None:
        print("ERROR: No free port in", PORTS, file=sys.stderr)
        print("Run stop_server.bat to close old processes.", file=sys.stderr)
        sys.exit(1)

    _install_windows_console_handler()
    atexit.register(_cleanup_runtime)
    signal.signal(signal.SIGINT, lambda *_: (_cleanup_runtime(), sys.exit(0)))
    signal.signal(signal.SIGTERM, lambda *_: (_cleanup_runtime(), sys.exit(0)))
    _write_runtime(port)

    print()
    print("=" * 50)
    print("  Warm Dialogue Assistant")
    print("  Set DEEPSEEK_API_KEY in .env before using AI")
    print(f"  Open in browser: http://127.0.0.1:{port}")
    print("  Close this window to stop the server")
    print("=" * 50)
    print()

    # Embedded Python (runtime/) does not put project root on sys.path via ._pth
    os.chdir(ROOT)
    root_str = str(ROOT)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    import uvicorn
    from app.main import app as fastapi_app

    # reload=False: avoids orphan child processes when closing the window
    uvicorn.run(
        fastapi_app,
        host="127.0.0.1",
        port=port,
        reload=False,
    )
    _cleanup_runtime()


if __name__ == "__main__":
    main()
