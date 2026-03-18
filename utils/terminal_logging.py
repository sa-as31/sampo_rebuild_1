import os
import sys
from datetime import datetime, timezone


_LOG_FILE_HANDLE = None
_INSTALLED = False


class _TeeStream:
    def __init__(self, *streams):
        self._streams = streams

    def write(self, data):
        for stream in self._streams:
            stream.write(data)
        return len(data)

    def flush(self):
        for stream in self._streams:
            stream.flush()

    def isatty(self):
        for stream in self._streams:
            if hasattr(stream, "isatty") and stream.isatty():
                return True
        return False


def _build_timestamped_filename(prefix="terminal_output", ext=".log"):
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{now}{ext}"


def setup_terminal_logging(train_dir, experiments_root, filename=None):
    global _LOG_FILE_HANDLE, _INSTALLED
    if _INSTALLED:
        return

    experiment_dir = os.path.join(train_dir, experiments_root)
    os.makedirs(experiment_dir, exist_ok=True)
    if filename is None:
        filename = _build_timestamped_filename()

    log_path = os.path.join(experiment_dir, filename)
    if os.path.exists(log_path):
        # Extremely rare (same second + same filename). Keep files unique anyway.
        filename = _build_timestamped_filename(prefix="terminal_output_dup")
        log_path = os.path.join(experiment_dir, filename)

    _LOG_FILE_HANDLE = open(log_path, "a", encoding="utf-8", buffering=1)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    _LOG_FILE_HANDLE.write(f"\n===== Training session started at {now} =====\n")
    _LOG_FILE_HANDLE.write(f"===== Log file: {filename} =====\n")

    sys.stdout = _TeeStream(sys.stdout, _LOG_FILE_HANDLE)
    sys.stderr = _TeeStream(sys.stderr, _LOG_FILE_HANDLE)
    _INSTALLED = True
