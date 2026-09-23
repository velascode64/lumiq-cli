from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

from ..registry.strategies import resolve
from .database import RunStore, utc_now


class Supervisor:
    def __init__(self, root: Path, state_dir: Path):
        self.root = root.resolve()
        self.state_dir = state_dir.expanduser()
        self.store = RunStore(self.state_dir / "lumiq.sqlite3")
        self.logs = self.state_dir / "logs"
        self.logs.mkdir(parents=True, exist_ok=True)

    def start(self, strategy_id: str, mode: str, parameters: dict[str, Any], env: dict[str, str]):
        strategy = resolve(self.root / "strategies", strategy_id)
        for row in self.store.all():
            if row["strategy_id"] == strategy_id and row["mode"] == mode and row["status"] in ("starting", "running"):
                try:
                    os.kill(row["pid"], 0)
                    raise RuntimeError(f"Strategy already running: {row['run_id']}")
                except ProcessLookupError:
                    self.store.update(row["run_id"], status="stopped", stopped_at=utc_now())

        run_id = uuid.uuid4().hex[:12]
        stdout = self.logs / f"{run_id}.stdout.log"
        stderr = self.logs / f"{run_id}.stderr.log"
        self.store.create(
            run_id=run_id,
            strategy_id=strategy_id,
            strategy_path=str(Path(strategy["module"]).resolve()),
            mode=mode,
            broker="alpaca",
            parameters=json.dumps(parameters, sort_keys=True),
            status="starting",
            pid=None,
            stdout_path=str(stdout),
            stderr_path=str(stderr),
        )
        command = [
            sys.executable,
            "-m",
            "lumiq.infrastructure.worker",
            "--strategy-path",
            strategy["module"],
            "--mode",
            mode,
            "--parameters",
            json.dumps(parameters),
            "--logfile",
            str(stdout),
        ]
        child_env = os.environ.copy()
        child_env.update(env)
        child_env["PYTHONPATH"] = os.pathsep.join(
            filter(None, [str(self.root.parent / "lumibot"), str(self.root), child_env.get("PYTHONPATH", "")])
        )
        with stdout.open("ab") as out, stderr.open("ab") as err:
            process = subprocess.Popen(
                command,
                cwd=self.root,
                env=child_env,
                stdout=out,
                stderr=err,
                start_new_session=True,
            )
        self.store.update(run_id, pid=process.pid, status="running", started_at=utc_now())
        return self.store.public(self.store.get(run_id))

    def stop(self, run_id: str):
        row = self.store.get(run_id)
        if row is None:
            raise KeyError(run_id)
        if row["pid"]:
            try:
                os.kill(row["pid"], signal.SIGTERM)
            except ProcessLookupError:
                pass
        self.store.update(run_id, status="stopped", stopped_at=utc_now())
        return self.store.public(self.store.get(run_id))

    def status(self, run_id: str | None = None):
        rows = [self.store.get(run_id)] if run_id else self.store.all()
        result = []
        for row in rows:
            if row is None:
                continue
            item = self.store.public(row)
            if row["pid"] and row["status"] in ("starting", "running"):
                try:
                    os.kill(row["pid"], 0)
                except ProcessLookupError:
                    self.store.update(row["run_id"], status="failed", stopped_at=utc_now(), error="process exited")
                    item = self.store.public(self.store.get(row["run_id"]))
            result.append(item)
        return result

    def logs_for(self, run_id: str, lines: int = 100):
        row = self.store.get(run_id)
        if row is None:
            raise KeyError(run_id)
        path = Path(row["stdout_path"])
        if not path.exists():
            return ""
        return "".join(path.read_text(errors="replace").splitlines(True)[-lines:])