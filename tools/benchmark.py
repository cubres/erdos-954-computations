#!/usr/bin/env python3
"""Compare generator configurations near a supplied prefix; do not publish as an audit."""
import argparse
import hashlib
import json
import os
import pathlib
import platform
import subprocess
import time


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seed", type=pathlib.Path, required=True)
    p.add_argument("--limit", type=int, default=1010000000000)
    p.add_argument("--output", type=pathlib.Path, required=True)
    p.add_argument("--workers", type=int, nargs="+", default=[1, 2, 4, 8])
    p.add_argument("--blocks", type=int, nargs="+", default=[33554432, 134217728])
    args = p.parse_args()
    root = pathlib.Path(__file__).resolve().parents[1]
    args.output.mkdir(parents=True, exist_ok=False)
    results = {"platform": platform.platform(), "logical_cpus": os.cpu_count(),
               "seed_sha256": sha(args.seed), "source_sha256": sha(root / "src/generate.cpp"),
               "executable_sha256": sha(root / "build/generate"),
               "independent_full_audit": False, "runs": []}
    for workers in args.workers:
        for block in args.blocks:
            prefix = args.output / f"w{workers}-b{block}"
            command = [str(root / "build/generate"), str(args.limit), str(prefix),
                       str(block), str(args.seed), str(workers)]
            start = time.monotonic()
            with prefix.with_suffix(".log").open("w") as log:
                subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
            summary = json.loads(pathlib.Path(str(prefix) + "_summary.json").read_text())
            summary["wall_seconds_including_startup"] = time.monotonic() - start
            positions = summary["processed_through"] - summary["seed_last"]
            summary["positions_per_second"] = positions / summary["seconds"]
            summary["term_csv_sha256"] = sha(pathlib.Path(str(prefix) + "_terms.csv"))
            results["runs"].append(summary)
            (args.output / "benchmarks.json").write_text(json.dumps(results, indent=2) + "\n")
            print(json.dumps({k: summary[k] for k in
                              ("workers", "block", "seconds", "positions_per_second")}), flush=True)
    if len({r["term_csv_sha256"] for r in results["runs"]}) != 1:
        raise RuntimeError("generator configurations produced different term lists")
    results["all_term_lists_identical"] = True
    (args.output / "benchmarks.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
