# Data, provenance, and verification scope

## Current release: v1.1.0 through 10¹³

The current data cover **every integer from 1 through 10¹³**, including the
tail after the last positive term, 9988075638050. There are 5,044,644 positive
terms; the fixed initial zero is excluded from the CSV.

| File | Meaning |
| --- | --- |
| `terms_1e13.csv.gz` | Gzip of `index,value`, one positive term per row |
| `gap_lengths_1e13.csv.gz` | Gzip of `index,left,right,gap`, one consecutive positive-term pair per row |
| `data/audit_1e13.json` | Independent interval audit, full stated range |
| `data/generator_1e13.json` | Original generator endpoint report |
| `data/manifest.json` | Current release hashes, sizes, source provenance, and extra exact queries |
| `data/manifest_1e12.json` | Archived manifest for the previous release |

The gap index is the left term's index, so row `n` describes `a_n` to `a_(n+1)`.
All 5,044,643 gap rows were checked against adjacent verified terms. There is no
initial 0-to-1 row and no unfinished tail row. This release includes no per-gap
error area or peak columns; the older format below remains available separately.

The independent auditor certified 9,955,087,392,768 positions using exact
endpoint enclosures and scanned the remaining 44,912,607,232 positions in
histogram leaves. These counts sum to 10¹³. Every greedy decision, both sides
of every contact, all zero-error positions, and the global maximum are covered.
See [the proof of the interval audit](interval-audit.md). The audit source and
binary hashes, source commit, and parameters are recorded in the manifest.
The same method matched historical exhaustive audit results through 10¹².
The redundant exhaustive scan at 10¹³ was stopped before completion; it is not
claimed as a second completed full audit of this release.

The maximum error is 1,168,643,713. The audit identifies its first and last
locations as 9011936754289 and 9011936754292. Separate Python pair-count queries
at every integer between those locations give errors 1168643713, 1168643712,
1168643712, 1168643713; thus exactly two positions attain the maximum.
The original 1,595,636-term audited prefix was also checked row for row.

Generation from the audited 10¹² seed took 18323.6 seconds using the bulk/byte
generator, without cumulative endpoint jumps. The interval audit took 1081.11
seconds. These are recorded timings on the development machine, not universal
performance estimates. The generator report retains `independently_audited:false`
because it describes generation alone; the separate `PASS` audit is the
verification authority.

To fetch the historical files instead, pass
`--manifest data/manifest_1e12.json` to `tools/fetch_data.py`.

## Historical release: v1.0.0 through 10¹²

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
| `data/manifest_1e12.json` | Historical release asset hashes, sizes, and original source hashes |

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
