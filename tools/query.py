#!/usr/bin/env python3
"""Exact counts, cumulative error areas, and index queries. Standard library only."""
import argparse
import bisect
import csv
import gzip
import json
from array import array


def read_terms(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    a = array("Q")
    with opener(path, "rt", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != ["index", "value"]:
            raise ValueError("expected header index,value")
        for index, row in enumerate(reader, 1):
            value = int(row["value"])
            if int(row["index"]) != index or value <= (a[-1] if a else 0):
                raise ValueError("invalid index or non-increasing terms")
            a.append(value)
    if not a or a[0] != 1:
        raise ValueError("expected a nonempty positive prefix starting at 1")
    return a


def count(a, x):
    j = bisect.bisect_right(a, x)
    total = j  # zero pairs
    i = 0
    while i < j:
        while j > i and a[i] + a[j - 1] > x:
            j -= 1
        if j <= i:
            break
        total += j - i
        i += 1
    return total


def cumulative_error(a, x):
    """Return sum(E(t), 1 <= t <= x) in O(A(x)) time and O(1) extra space.

    A pair of sum s contributes x-s+1 to the cumulative count. The
    decreasing right pointer maintains the sum of each eligible pair row.
    All arithmetic uses Python integers, including areas beyond 64 bits.
    """
    j = bisect.bisect_right(a, x)
    row_sum = sum(a[i] for i in range(j))
    total = j * (x + 1) - row_sum  # weighted zero pairs
    i = 0
    while i < j:
        while j > i and a[i] + a[j - 1] > x:
            j -= 1
            row_sum -= a[j]
        if j <= i:
            break
        total += (j - i) * (x + 1 - a[i]) - row_sum
        row_sum -= a[i]
        i += 1
    return total - x * (x + 1) // 2


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("terms")
    p.add_argument("--limit", type=int, required=True, help="known complete bound for this dataset")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--x", type=int)
    g.add_argument("--index", type=int)
    p.add_argument("--area", action="store_true", help="with --x, also return sum_E = sum(E(t), 1 <= t <= x)")
    args = p.parse_args()
    if args.area and args.x is None:
        p.error("--area is available only with --x")
    a = read_terms(args.terms)
    if args.limit < a[-1]:
        p.error("declared completeness bound precedes the last term")
    if args.x is not None:
        if not 0 <= args.x <= args.limit:
            p.error("x must lie in the declared complete range")
        r = count(a, args.x)
        result = {"x": args.x, "A": bisect.bisect_right(a, args.x), "R": r, "E": r - args.x}
        if args.area:
            result["sum_E"] = cumulative_error(a, args.x)
    else:
        if not 0 <= args.index <= len(a):
            p.error("index outside this prefix")
        result = {"index": args.index, "value": 0 if args.index == 0 else a[args.index - 1]}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
