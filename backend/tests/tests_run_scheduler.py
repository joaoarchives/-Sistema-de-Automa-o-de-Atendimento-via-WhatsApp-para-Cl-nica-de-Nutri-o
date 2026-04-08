import json
from pathlib import Path

import run_scheduler as run_scheduler_module


def test_write_health_snapshot_cria_arquivo(tmp_path, monkeypatch):
    health_file = tmp_path / "scheduler-health.json"
    monkeypatch.setattr(run_scheduler_module, "_HEALTH_FILE_PATH", health_file)
    monkeypatch.setattr(
        run_scheduler_module,
        "descrever_jobs_scheduler",
        lambda: [{"id": "job-1", "trigger": "interval", "kwargs": {"minutes": 1}}],
    )

    run_scheduler_module._write_health_snapshot(
        status="running",
        lock_acquired=True,
        scheduler_running=True,
        extra={"message": "ok"},
    )

    payload = json.loads(health_file.read_text(encoding="utf-8"))
    assert payload["status"] == "running"
    assert payload["lock_acquired"] is True
    assert payload["scheduler_running"] is True
    assert payload["message"] == "ok"
    assert payload["jobs"][0]["id"] == "job-1"


def test_write_health_snapshot_informa_role(tmp_path, monkeypatch):
    health_file = tmp_path / "scheduler-health.json"
    monkeypatch.setattr(run_scheduler_module, "_HEALTH_FILE_PATH", health_file)
    monkeypatch.setattr(run_scheduler_module.os, "getenv", lambda key, default=None: "scheduler" if key == "APP_ROLE" else default)
    monkeypatch.setattr(run_scheduler_module, "descrever_jobs_scheduler", lambda: [])

    run_scheduler_module._write_health_snapshot(
        status="starting",
        lock_acquired=False,
        scheduler_running=False,
    )

    payload = json.loads(Path(health_file).read_text(encoding="utf-8"))
    assert payload["app_role"] == "scheduler"
    assert payload["status"] == "starting"
