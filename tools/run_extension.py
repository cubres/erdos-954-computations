#!/usr/bin/env python3
"""Run generation then a full audit, with durable logs and a machine-readable status."""
import argparse
import hashlib
import json
import pathlib
import signal
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, required=True)
    parser.add_argument("--seed", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--block", type=int, default=134217728)
    parser.add_argument("--audit-block", type=int, default=33554432)
    args = parser.parse_args()
    root = pathlib.Path(__file__).resolve().parents[1]
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    status_path = out / "pipeline.json"
    state = {"target": args.limit, "started_unix": time.time(), "stage": "generation"}
    child = None
    interrupted = False

    def write():
        temp = status_path.with_suffix(".tmp")
        temp.write_text(json.dumps(state, indent=2) + "\n")
        temp.replace(status_path)

    def stop(signum, frame):
        nonlocal interrupted
        interrupted = True
        if child is not None and child.poll() is None:
            child.terminate()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    commands = [
        ("generation", [str(root / "build/generate"), str(args.limit), str(out / "result"),
                        str(args.block), str(args.seed.resolve()), str(args.workers)]),
        ("audit", [str(root / "build/audit"), str(out / "result_terms.csv"), str(args.limit),
                   str(out / "audit.json"), str(args.workers), str(args.audit_block)])]
    write()
    for stage, command in commands:
        if interrupted:
            state["stage"] = "STOPPED"
            write()
            return 3
        state["stage"] = stage
        state["stage_started_unix"] = time.time()
        write()
        with (out / f"{stage}.log").open("w") as log:
            child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
            state["child_pid"] = child.pid
            write()
            code = child.wait()
        if code:
            state.update(stage="STOPPED" if interrupted or code == 3 else "FAILED", returncode=code)
            write()
            return code
    h = hashlib.sha256()
    with (out / "result_terms.csv").open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    state.update(stage="AUDITED", completed_unix=time.time(), terms_sha256=h.hexdigest())
    state.pop("child_pid", None)
    write()
    print(json.dumps(state))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
