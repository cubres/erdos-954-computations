# Data, provenance, and verification scope

## Current release: v1.2.0 through 10¹⁴

The current data cover **every integer from 1 through 10¹⁴**, including the
tail after the last positive term, 99931466447235. There are 15,956,975 positive
terms; the fixed initial zero is excluded from the CSV.

| File | Meaning |
| --- | --- |
| `terms_1e14.csv.gz` | Gzip of `index,value`, one positive term per row |
| `gap_lengths_1e14.csv.gz` | Gzip of `index,left,right,gap`, one consecutive positive-term pair per row |
| `data/audit_1e14.json` | Independent interval audit, full stated range |
| `data/generator_1e14.json` | Original generator endpoint report |
| `data/manifest.json` | Current release hashes, sizes, source provenance, and extra exact queries |
| `data/manifest_1e13.json` | Archived manifest for the previous release |
| `data/gap_statistics_1e14.json` | Reproducible completed-gap length summaries by decade |

All 15,956,974 completed-gap rows were separately checked against consecutive
audited terms. The gap index is the left term's index. There is no initial
0-to-1 row, no unfinished tail row, and no per-gap error area or peak column.
The earlier 5,044,644-term audited prefix was checked row for row.

The independent auditor certified 99,809,442,283,520 positions using exact
endpoint enclosures and scanned the remaining 190,557,716,480 positions in
histogram leaves. These counts sum to 10¹⁴. Every greedy decision, both sides
of every contact, all zero-error positions, and the global maximum are covered.
See [the interval-audit proof](interval-audit.md). This is a complete audit by
the stated method; a separate full exhaustive scan of 10¹⁴ was not performed.
The method was previously compared with exhaustive audit results through 10¹².

The maximum error is 7,374,280,256, attained at exactly the five consecutive
integers from 97529985405572 through 97529985405576. The independent auditor
identified the first and last maximizers; separate Python pair-count queries
checked every intervening integer and both neighbors. The manifest records
those exact values and additional queries at the last contact and cutoff.
The longest completed gap has length 299,712,984,412, from 97454293430918 to
97754006415330, and its left term has index 15,768,573.

Generation from the audited 10¹³ seed took 8131.7 seconds using cumulative
endpoint jumps. The independent interval audit took 8802.73 seconds. Both ran
on the Intel Core i5-7400 development machine with four workers; other work
shared the machine. Source, binary and input hashes and all run parameters
are recorded in the manifest. The generator report retains
`independently_audited:false` because it describes generation alone; the
separate `PASS` audit is the verification authority.

For a historical release, pass `--manifest data/manifest_1e13.json` or
`--manifest data/manifest_1e12.json` to `tools/fetch_data.py`.

## Gap-length summaries

`tools/gap_stats.py` reads an immutable positive-term CSV or gzip CSV in one
streaming pass. It validates every input row and records the SHA-256 and byte
count of the exact uncompressed input. The caller supplies its known complete
bound with `--limit`; the tool does not prove that bound or audit greedy
decisions. An optional `--through N` summarizes an earlier cutoff while still
validating and hashing the entire input.

The [recorded summary through 10¹⁴](../data/gap_statistics_1e14.json) identifies
its input by the uncompressed SHA-256 recorded for the independently audited
v1.2.0 term list. It contains 15,956,974 completed gaps. Its highest decade,
with left endpoints in `[10^13,10^14)`, includes only gaps whose right endpoints
are at most 10¹⁴; the final unfinished tail is excluded.

Only completed pairs of consecutive positive terms `(p,q)` with `q <= N` are
counted. The initial pair `(0,1)` and the unfinished interval after the final
term are excluded. The pair belongs to the decade `10^k <= p < 10^(k+1)`, even
when `q` lies in a later decade. A decade with no counted gaps is omitted.

Each decade records the number of gaps, sum of their lengths, minimum and
maximum length, the first gap attaining that maximum, and an exact mean as a
numerator/denominator pair. The `above_normalized_threshold` list is aligned
with `normalized_thresholds = [1,2,4,8,16,32,64,128,256,512,1024]`. Its entry for
`t` counts precisely the gaps satisfying `(q-p)^2 > t^2*p`; equality is excluded.
Python integers keep these comparisons exact, including beyond 64-bit squares.
The reported checksum identifies the input bytes, not a proof of correctness.

For a small example requiring no download:

```sh
python3 tools/gap_stats.py data/sample_1e6.csv --limit 1000000
```

## Historical release: v1.1.0 through 10¹³

The v1.1.0 data cover **every integer from 1 through 10¹³**, including the
tail after the last positive term, 9988075638050. There are 5,044,644 positive
terms; the fixed initial zero is excluded from the CSV.

| File | Meaning |
| --- | --- |
| `terms_1e13.csv.gz` | Gzip of `index,value`, one positive term per row |
| `gap_lengths_1e13.csv.gz` | Gzip of `index,left,right,gap`, one consecutive positive-term pair per row |
| `data/audit_1e13.json` | Independent interval audit, full stated range |
| `data/generator_1e13.json` | Original generator endpoint report |
| `data/manifest_1e13.json` | Historical release hashes, sizes, source provenance, and extra exact queries |
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

To fetch these historical files, pass
`--manifest data/manifest_1e13.json` to `tools/fetch_data.py`.

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
