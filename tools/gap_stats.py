#!/usr/bin/env python3
"""Exact, streaming length summaries of completed positive-term gaps."""
import argparse
import gzip
import hashlib
import json
import pathlib


THRESHOLDS = tuple(1 << exponent for exponent in range(11))


def summarize(path, limit, through=None):
    """Validate the whole input; summarize consecutive pairs ending by through.

    The declared limit is a completeness assertion supplied by the caller,
    not a greedy-sequence audit. Hashes describe the exact uncompressed bytes.
    """
    if limit < 1 or through is not None and not 0 <= through <= limit:
        raise ValueError("require limit >= 1 and 0 <= through <= limit")
    through = limit if through is None else through
    path = pathlib.Path(path)
    opener = gzip.open if path.suffix == ".gz" else open
    digest = hashlib.sha256()
    bins = {}
    rows = previous = selected_terms = byte_count = 0
    stat_before = path.stat()
    with opener(path, "rb") as stream:
        header = stream.readline()
        if header.rstrip(b"\r\n") != b"index,value" or not header.endswith(b"\n"):
            raise ValueError("expected header index,value")
        digest.update(header)
        byte_count += len(header)
        for line in stream:
            digest.update(line)
            byte_count += len(line)
            if not line.endswith(b"\n"):
                raise ValueError("input ends with an incomplete line")
            fields = line.rstrip(b"\r\n").split(b",")
            if len(fields) != 2 or not all(field.isdigit() for field in fields):
                raise ValueError("expected two unsigned decimal integers per row")
            index, value = map(int, fields)
            if index != rows + 1 or value <= previous or rows == 0 and value != 1:
                raise ValueError("invalid index or non-increasing positive prefix")
            if value > limit:
                raise ValueError("declared completeness bound precedes the last term")
            if value <= through:
                selected_terms += 1
                if previous:
                    decade = len(str(previous)) - 1
                    if decade not in bins:
                        bins[decade] = {
                            "left_at_least": 10 ** decade,
                            "left_below": 10 ** (decade + 1),
                            "gaps": 0, "sum_length": 0,
                            "min_length": None, "max_length": None,
                            "first_maximum": None,
                            "exceeded_count_histogram": [0] * (len(THRESHOLDS) + 1),
                        }
                    item = bins[decade]
                    gap = value - previous
                    item["gaps"] += 1
                    item["sum_length"] += gap
                    if item["min_length"] is None or gap < item["min_length"]:
                        item["min_length"] = gap
                    if item["max_length"] is None or gap > item["max_length"]:
                        item["max_length"] = gap
                        item["first_maximum"] = {"index": rows, "left": previous, "right": value}
                    # 4**j * previous < gap**2 iff
                    # 4**j <= (gap**2 - 1) // previous. This counts the
                    # fixed power-of-two thresholds without floating point.
                    ratio_floor = (gap * gap - 1) // previous
                    exceeded = min(len(THRESHOLDS), (ratio_floor.bit_length() + 1) // 2)
                    item["exceeded_count_histogram"][exceeded] += 1
            rows += 1
            previous = value
    if rows == 0:
        raise ValueError("expected a nonempty positive prefix starting at 1")
    stat_after = path.stat()
    if (stat_before.st_dev, stat_before.st_ino, stat_before.st_size, stat_before.st_mtime_ns) != (
            stat_after.st_dev, stat_after.st_ino, stat_after.st_size, stat_after.st_mtime_ns):
        raise ValueError("input changed while it was being read; use an immutable snapshot")
    for item in bins.values():
        histogram = item.pop("exceeded_count_histogram")
        item["above_normalized_threshold"] = [
            sum(histogram[index + 1:]) for index in range(len(THRESHOLDS))]
        item["mean_length"] = {"numerator": item["sum_length"], "denominator": item["gaps"]}
    return {
        "schema_version": 1,
        "input": {"filename": path.name, "gzip": path.suffix == ".gz",
                  "uncompressed_sha256": digest.hexdigest(), "uncompressed_bytes": byte_count,
                  "positive_terms": rows, "last_term": previous},
        "declared_complete_through": limit,
        "summarized_through": through,
        "independently_audited_by_this_tool": False,
        "boundary_policy": {
            "gaps": "consecutive positive terms (p,q), with q <= summarized_through",
            "decade": "10^k <= p < 10^(k+1), including gaps crossing a decade boundary",
            "normalization": "strict g^2 > t^2*p, where g=q-p and t is the threshold",
            "excluded": "initial gap (0,1) and every unfinished tail",
            "completeness": "caller-supplied limit; structural validation is not an audit",
        },
        "normalized_thresholds": list(THRESHOLDS),
        "positive_terms_through_cutoff": selected_terms,
        "completed_gaps": max(0, selected_terms - 1),
        "decades": [bins[decade] for decade in sorted(bins)],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("terms", type=pathlib.Path, help="immutable index,value CSV or .csv.gz")
    parser.add_argument("--limit", type=int, required=True, help="known complete bound for the entire input")
    parser.add_argument("--through", type=int, help="optional smaller cutoff; the entire input is still validated")
    args = parser.parse_args()
    try:
        result = summarize(args.terms, args.limit, args.through)
    except (ValueError, OSError, EOFError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
