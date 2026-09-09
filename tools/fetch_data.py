#!/usr/bin/env python3
"""Download versioned release assets and verify both gzip and raw-content SHA-256."""
import argparse
import gzip
import hashlib
import json
import pathlib
import urllib.request


def digest(stream):
    h = hashlib.sha256()
    size = 0
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        h.update(chunk)
        size += len(chunk)
    return h.hexdigest(), size


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=pathlib.Path, default=pathlib.Path("runs/data"))
    p.add_argument("--manifest", type=pathlib.Path,
                   default=pathlib.Path(__file__).resolve().parents[1] / "data/manifest.json")
    p.add_argument("--terms-only", action="store_true")
    args = p.parse_args()
    manifest = json.loads(args.manifest.read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    for asset in manifest["assets"]:
        if args.terms_only and asset["kind"] != "terms":
            continue
        filename = asset["filename"]
        if pathlib.Path(filename).name != filename:
            raise ValueError("asset filename must be a basename")
        dest = args.output / filename
        temp = dest.with_name(dest.name + ".part")
        if not dest.exists():
            request = urllib.request.Request(asset["url"], headers={"User-Agent": "erdos-954-computations"})
            with urllib.request.urlopen(request, timeout=120) as response, temp.open("wb") as out:
                for chunk in iter(lambda: response.read(1024 * 1024), b""):
                    out.write(chunk)
            candidate = temp
        else:
            candidate = dest
        with candidate.open("rb") as f:
            if digest(f) != (asset["sha256"], asset["bytes"]):
                raise ValueError(f"compressed checksum/size mismatch: {candidate}")
        with gzip.open(candidate, "rb") as f:
            if digest(f) != (asset["uncompressed_sha256"], asset["uncompressed_bytes"]):
                raise ValueError(f"uncompressed checksum/size mismatch: {candidate}")
        if candidate == temp:
            temp.replace(dest)
        print(f"PASS {dest}: compressed and uncompressed hashes verified")


if __name__ == "__main__":
    main()
