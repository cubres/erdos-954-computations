# Data, provenance, and verification scope

The v1.0.0 data cover **every integer from 1 through 10¹²**, not 10¹² sequence
terms. The final positive term is 999090255890. The full audit also verifies the
remaining interval between that term and 10¹², where no new term is inserted.
There are 1,595,636 positive terms; the fixed initial zero is not in the CSV.

## Files

| File | Meaning |
| --- | --- |
| `terms_1e12.csv.gz` | Gzip of `index,value`, one positive term per row |
| `gaps_1e12.csv.gz` | Gzip of completed-gap statistics, one consecutive positive-term pair per row |
| `data/audit_1e12.json` | Historical independent full-range audit report |
| `data/generator_1e12.json` | Historical generator summary and power-of-ten checkpoints |
| `data/sample_1e6.csv` | Complete positive prefix through 10⁶ for immediate small queries |
| `data/manifest.json` | Release asset hashes, sizes, and original source hashes |

Gaps have columns `left,right,length,max_error,first_peak,error_area`.
For a gap with endpoints `left,right`, `length=right-left`, `max_error` is the
maximum of `E(x)` for `left<=x<right`, `first_peak` is its first location, and
`error_area` is the sum of `E(x)` on that integer interval. When the maximum is
zero, `first_peak=0` is a sentinel. There is no row for the unfinished final gap,
nor for the initial interval from 0 to 1.

## What was independently checked

The historical final-list auditor reconstructed all positive unordered pair sums
in 29,803 blocks of at most 33,554,432 integers, using four workers. It checked
every greedy insertion decision, the nonnegative error at every integer, both
sides of every contact, the global maximum and its first/last location, the
number of zero-error positions, and the endpoint count. Its report is `PASS`.

The term CSV's completeness and correctness have therefore been independently
audited throughout the stated range. Gap lengths follow directly from adjacent
verified terms and are separately checked when packaging the release. The
per-gap error areas, per-gap maxima/locations, and maximum arrival multiplicity
are **generator-reported** quantities: the historical auditor did not separately
certify those additional fields. A checksum authenticates a file, not its
mathematical contents.

## Reproduce the historical run

The unchanged programs in `reference/` generated and audited this release:

```sh
make build/reference
c++ -O3 -std=c++17 -pthread reference/verify_offline_parallel.cpp -o build/historical-audit
./build/reference 1000000000000 runs/reproduce 33554432
./build/historical-audit runs/reproduce_terms.csv 1000000000000 runs/reproduce_audit.json 4 33554432
```

Generation took 7937.69 seconds and independent auditing took 3857.9 seconds on
an Intel Core i5-7400 (4 cores, 3.00 GHz, 8 GiB RAM). These are recorded elapsed
times for those historical executions, not a universal performance guarantee.
CSV content is deterministic; JSON timing fields vary on reproduction.

The public programs in `src/` add stricter input handling. The generator also
uses a smaller checked histogram and exact bulk steps; compare its term CSV with
the release and use the independent auditor for any extension.

All numeric datasets are made available under CC0 1.0. No claim of mathematical
priority, theorem proof, or proof of the asymptotic conjecture is made by a
finite data release.
