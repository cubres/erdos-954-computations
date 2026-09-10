# Erdős #954: exact computations

[![Tests](https://github.com/cubres/erdos-954-computations/actions/workflows/test.yml/badge.svg)](https://github.com/cubres/erdos-954-computations/actions/workflows/test.yml)

Reproducible C++ computation and independent verification of the greedy sequence
constructed by Kenneth Rosen, associated with [Erdős problem #954](https://www.erdosproblems.com/954).

**Released, fully audited range: every integer through `1,000,000,000,000` (10¹²).**
This includes **1,595,636 positive sequence terms**. The bounds 10¹³ and 10¹⁵ are
extension targets, **not completed datasets**. Finite computations do not settle
the asymptotic question.

## The sequence and counting convention

Set $a_0=0$ and $a_1=1$. Once $a_0,\ldots,a_k$ are chosen, take $a_{k+1}$ to be
the smallest integer $n$ for which

```math
\left|\{(i,j):0\leq i\leq j\leq k,\ j\geq1,\ a_i+a_j\leq n\}\right|\lt n.
```

For the resulting infinite sequence, write

```math
R(x)=\left|\{(i,j):0\leq i\leq j,\ j\geq1,\ a_i+a_j\leq x\}\right|,\qquad E(x)=R(x)-x.
```

Pairs are unordered; diagonal pairs are included; pairs $(0,a_j)$ are included;
the pair $(0,0)$ is excluded. The sequence starts
`0, 1, 3, 5, 9, 13, 17, 24, 31, 38, 45, ...`.
CSV files contain only positive terms, with indices starting at 1.

The problem asks whether $R(x)=x+O(x^{1/4+o(1)})$.
The original source is P. Erdős, [*Problems and results on combinatorial number theory III*](https://users.renyi.hu/~p_erdos/1977-27.pdf),
*Number Theory Day*, Lecture Notes in Mathematics 626 (1977), pp. 43–72, p. 71.
See also [T. F. Bloom's problem page](https://www.erdosproblems.com/954)
and [OEIS A390642](https://oeis.org/A390642).

## Download the data

The [v1.0.0 release](https://github.com/cubres/erdos-954-computations/releases/tag/v1.0.0)
contains compressed term and completed-gap CSVs. [The data manifest](data/manifest.json)
records compressed and uncompressed SHA-256 hashes, sizes, scope, and provenance.
The [full audit report](data/audit_1e12.json) records verification of every integer,
including every insertion and every position at which no insertion was made.

```sh
python3 tools/fetch_data.py --output runs/data
python3 tools/query.py runs/data/terms_1e12.csv.gz --limit 1000000000000 --x 1000000000000
```

Add `--area` to return the exact cumulative error `sum_E = E(1) + ... + E(x)`.
The query uses weighted pair sums in O(A(x)) time and constant extra space after
loading the terms; it does not scan every integer through `x`. Python integers
keep large areas exact. Subtract two prefix areas to obtain an interval's area.

| Audited quantity | Value |
| --- | ---: |
| Positive terms at or below 10¹² | 1,595,636 |
| Last term at or below 10¹² | 999,090,255,890 |
| R(10¹²) | 1,000,025,288,916 |
| E(10¹²) | 25,288,916 |
| Maximum E(x), 1 ≤ x ≤ 10¹² | 101,328,126 |
| Position of that maximum (unique) | 843,375,334,188 |
| Positions with E(x) = 0, 1 ≤ x ≤ 10¹² | 5,874,526 |

The longest completed gap in the term list is 3,593,860,818, between
954,510,269,998 and 958,104,130,816. Per-gap error areas and peaks are additional
generator outputs; the historical independent audit did not individually
certify those extra columns. See [formats and verification scope](docs/data.md).

## Build and reproduce

Requires a C++17 compiler with `std::filesystem`, Make, and Python 3.9+.
Tested in CI on Linux and macOS. No Python packages are required.

```sh
make
make test
mkdir -p runs
./build/generate 100000000 runs/example 33554432
./build/audit runs/example_terms.csv 100000000 runs/example_audit.json 4 8388608
```

The generator writes a term CSV and a progress/endpoint JSON. It uses an exact
bulk summation optimization and checks its final cumulative count independently.
**Generator completion is not full verification:** run the separate auditor
before describing a new range as audited.

The auditor reconstructs pair sums from the final list, independently initializes
each block, and checks every greedy decision and the nonnegativity of the error.
It also recounts zero-error positions and the global error maximum.

## Extend or resume a computation

```sh
gzip -dc runs/data/terms_1e12.csv.gz > runs/seed.csv
./build/generate 10000000000000 runs/extension_1e13 134217728 runs/seed.csv 4
./build/audit runs/extension_1e13_terms.csv 10000000000000 runs/audit_1e13.json 4 33554432
```

The seed must contain a complete, correct prefix. The generator checks CSV
structure and the final contact, then recomputes from just after its last term.
It does **not** fully verify the seed. The output includes the seed terms, so a
completed output is a self-contained prefix suitable for the full auditor.

The last argument controls histogram workers (default 1); use `-` instead of a
seed filename to start from scratch with multiple workers. Only pair preparation
is parallel; benchmark worker counts and block sizes on the chosen hardware.

`SIGINT`/`SIGTERM` request a stop after the current block (exit code 3). Progress
JSON and flushed CSV are saved at least every 30 seconds at block boundaries.
To resume, use the saved CSV as the seed and choose a **new output prefix**.
Existing outputs are never overwritten. After a hard kill or power failure, use
a complete saved prefix; a truncated final CSV line is rejected. Persistent
backups are necessary on a disposable cloud VM.

The optimized histogram stores one byte per position and aborts if any arrival
count would exceed 255; it never silently wraps. Its supported input range is
1 through 10¹⁵, which is an arithmetic guard, **not a tested computation bound**.
See [the algorithm](docs/algorithm.md) and [compute options and benchmarks](docs/compute.md)
before launching a large run.

## Repository contents

- `src/`: optimized generator and independent auditor with strict input checks.
- `reference/`: unchanged historical programs used for the released 10¹² run.
- `tools/`: checksummed downloads and exact count queries for CSV or gzip data.
- `tests/`: direct-definition checks, comparison against the reference generator,
  block boundaries, resume equivalence, and rejection of corrupted inputs.
- `data/`: small sample, audit report, generator summary, and release manifest.

Contributions are welcome: reproducible timings, independently audited extensions,
portability improvements, and bug reports with minimal examples. Include the
source commit, commands, hardware, hashes, and a separate audit for any new dataset.

## License and attribution

Code is [MIT licensed](LICENSE). The numeric datasets are dedicated to the public
domain under [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).
Please cite the release and commit for reproducibility, and credit the original
mathematical sources above. Prepared by Cubres with AI-assisted development;
verification procedures and their limits are documented explicitly.
