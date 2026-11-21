"""Runs ``mopidy local scan`` in the background for the Settings page.

Mopidy-Local reads its SQLite library on every query, so new tracks show up
as soon as the scan has committed them; no restart is needed.
"""

from __future__ import annotations

import collections
import logging
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

TAIL_LINES = 40

FOUND_FILES = re.compile(r"Found (\d+) files in")
TO_UPDATE = re.compile(r"Found (\d+) tracks which need to be updated")
PROGRESS = re.compile(r"Scanned (\d+) of (\d+) files")
REMOVED = re.compile(r"Removing (\d+) missing tracks")


def scan_command(full: bool) -> list[str]:
    # The console script next to the running interpreter, else whatever is on PATH.
    sibling = os.path.join(os.path.dirname(sys.executable), "mopidy")
    exe = sibling if os.path.exists(sibling) else shutil.which("mopidy") or "mopidy"
    return [exe, "local", "scan", *(["--force"] if full else [])]


def _lower_priority() -> None:
    os.nice(10)  # keep playback smooth while the scan reads tags


class LocalScanner:
    def __init__(self, command=scan_command) -> None:
        self.command = command
        self._lock = threading.Lock()
        self._proc: subprocess.Popen | None = None
        self._status: dict[str, Any] = {"state": "idle"}

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {**self._status, "tail": list(self._status.get("tail", ()))}

    def start(self, full: bool = False) -> bool:
        """Start a scan; False if one is already running."""
        with self._lock:
            if self._proc and self._proc.poll() is None:
                return False
            env = {**os.environ, "COLUMNS": "1000", "NO_COLOR": "1", "TERM": "dumb"}
            self._proc = subprocess.Popen(
                self.command(full),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
                env=env,
                preexec_fn=_lower_priority if os.name == "posix" else None,
            )
            self._status = {
                "state": "running",
                "full": full,
                "started": time.time(),
                "finished": None,
                "files": None,  # audio files found in media_dir
                "total": None,  # files that need (re)scanning
                "scanned": 0,
                "removed": 0,
                "warnings": 0,
                "exit_code": None,
                "tail": collections.deque(maxlen=TAIL_LINES),
            }
            proc = self._proc
        logger.info("Melody: started %s local scan", "full" if full else "a")
        threading.Thread(
            target=self._follow, args=(proc,), name="melody-scan", daemon=True
        ).start()
        return True

    def _follow(self, proc: subprocess.Popen) -> None:
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.rstrip()
            if line:
                self._parse(line)
        code = proc.wait()
        with self._lock:
            self._status["exit_code"] = code
            self._status["finished"] = time.time()
            self._status["state"] = "done" if code == 0 else "failed"
        logger.info("Melody: local scan finished with exit code %s", code)

    def _parse(self, line: str) -> None:
        with self._lock:
            s = self._status
            s["tail"].append(line)
            if "WARNING" in line:
                s["warnings"] += 1
            if m := FOUND_FILES.search(line):
                s["files"] = int(m.group(1))
            elif m := TO_UPDATE.search(line):
                s["total"] = int(m.group(1))
            elif m := PROGRESS.search(line):
                s["scanned"], s["total"] = int(m.group(1)), int(m.group(2))
            elif m := REMOVED.search(line):
                s["removed"] = int(m.group(1))
