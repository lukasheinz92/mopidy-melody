from __future__ import annotations

import sys
import time

from mopidy_melody.scan import LocalScanner, scan_command

FAKE_OUTPUT = [
    "INFO     Finding files in file:///media/music ...",
    "INFO     Found 250 files in file:///media/music",
    "INFO     Checking 0 tracks from library",
    "INFO     Removing 3 missing tracks",
    "INFO     Found 250 tracks which need to be updated",
    "INFO     Scanning...",
    "WARNING  Failed scanning file:///media/music/broken.mp3: boom",
    "INFO     Scanned 100 of 250 files in 10.000s, ~15s left",
    "INFO     Scanned 250 of 250 files in 25.000s.",
    "INFO     Done scanning",
]


def fake_command(lines, code=0):
    script = f"import sys; print({chr(10).join(lines)!r}); sys.exit({code})"
    return lambda full: [sys.executable, "-c", script]


def wait(scanner, timeout=10):
    deadline = time.time() + timeout
    while scanner.status()["state"] == "running":
        assert time.time() < deadline, "scan did not finish"
        time.sleep(0.05)
    return scanner.status()


def test_scan_command():
    assert scan_command(False)[-2:] == ["local", "scan"]
    assert scan_command(True)[-1] == "--force"


def test_progress_is_parsed():
    scanner = LocalScanner(fake_command(FAKE_OUTPUT))
    assert scanner.status() == {"state": "idle", "tail": []}
    assert scanner.start(full=True)
    status = wait(scanner)
    assert status["state"] == "done"
    assert status["full"] is True
    assert status["files"] == 250
    assert (status["scanned"], status["total"]) == (250, 250)
    assert status["removed"] == 3
    assert status["warnings"] == 1
    assert status["tail"][-1].endswith("Done scanning")
    assert status["finished"] >= status["started"]


def test_failure_and_single_instance():
    script = (
        "import sys, time; print('ERROR boom', flush=True); "
        "time.sleep(0.5); sys.exit(1)"
    )
    scanner = LocalScanner(lambda full: [sys.executable, "-c", script])
    assert scanner.start()
    assert not scanner.start()  # already running
    status = wait(scanner)
    assert status["state"] == "failed"
    assert status["exit_code"] == 1
    assert status["tail"] == ["ERROR boom"]
    assert scanner.start()  # can run again afterwards
    wait(scanner)
