# Erdős #954: exact computations

[![Tests](https://github.com/cubres/erdos-954-computations/actions/workflows/test.yml/badge.svg)](https://github.com/cubres/erdos-954-computations/actions/workflows/test.yml)

Reproducible C++ computation and independent verification of the greedy sequence
constructed by Kenneth Rosen, associated with [Erdős problem #954](https://www.erdosproblems.com/954).

**Released, fully audited range: every integer through `10,000,000,000,000` (10¹³).**
This includes **5,044,644 positive sequence terms**. The bounds 10¹⁴ and 10¹⁵ are
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

The [v1.1.0 release](https://github.com/cubres/erdos-954-computations/releases/tag/v1.1.0)
contains compressed term and completed-gap-length CSVs. [The data manifest](data/manifest.json)
records compressed and uncompressed SHA-256 hashes, sizes, scope, and provenance.
The [full audit report](data/audit_1e13.json) records verification of every integer,
including every insertion and every position at which no insertion was made.
Exact interval inequalities certify 99.55% of the range; histogram scans check
the remainder. Both methods use the final term list independently of generation.

```sh
python3 tools/fetch_data.py --output runs/data
python3 tools/query.py runs/data/terms_1e13.csv.gz --limit 10000000000000 --x 10000000000000
```

Add `--area` to return the exact cumulative error `sum_E = E(1) + ... + E(x)`.
The query uses weighted pair sums in O(A(x)) time and constant extra space after
loading the terms; it does not scan every integer through `x`. Python integers
keep large areas exact. Subtract two prefix areas to obtain an interval's area.

| Audited quantity | Value |
| --- | ---: |
| Positive terms at or below 10¹³ | 5,044,644 |
| Last term at or below 10¹³ | 9,988,075,638,050 |
| R(10¹³) | 10,000,134,675,635 |
| E(10¹³) | 134,675,635 |
| Maximum E(x), 1 ≤ x ≤ 10¹³ | 1,168,643,713 |
| Positions of that maximum (exactly two) | 9,011,936,754,289 and 9,011,936,754,292 |
| Positions with E(x) = 0, 1 ≤ x ≤ 10¹³ | 18,745,473 |

The longest completed gap is 40,444,422,225, between 8,996,426,031,585 and
9,036,870,453,810. The new gap file contains endpoints and lengths only.
The historical [v1.0.0 release](https://github.com/cubres/erdos-954-computations/releases/tag/v1.0.0)
through 10¹² remains available, with its original gap-statistics format.
See [formats and verification scope](docs/data.md).

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

Append `--jump` to enable cumulative endpoint jumps between histogram blocks:

```sh
./build/generate 1000000000 runs/jump_example 65536 - 4 --jump
```

When the surplus is large enough to rule out every insertion in the next
interval, this mode recounts its endpoint directly and avoids enumerating its
pair arrivals. The ordinary histogram path handles the remaining positions.
The [correctness argument](docs/algorithm.md#cumulative-endpoint-jumps) uses an
exact surplus inequality. The optimization is optional; the default generator
and extension pipeline retain their existing behavior.

The auditor reconstructs pair sums from the final list, independently initializes
each block, and checks every greedy decision and the nonnegativity of the error.
It also recounts zero-error positions and the global error maximum. Monotone
partner pointers avoid repeating binary searches for every pair row; the
auditor still visits every integer in its declared range.

An alternative independent auditor uses exact endpoint enclosures to certify
whole intervals. It checks the same greedy decisions, zero-error count and
global maximum, while scanning only intervals that its bounds cannot certify:

```sh
./build/audit_intervals runs/example_terms.csv 100000000 runs/interval_audit.json 2 4096 67108864
```

Its report distinguishes positions scanned from positions certified by an
inequality. All integers in the declared range are covered. See the
[correctness argument and tuning parameters](docs/interval-audit.md).
The extension pipeline continues to use the exhaustive `build/audit` by default.

## Extend or resume a computation

```sh
gzip -dc runs/data/terms_1e13.csv.gz > runs/seed.csv
python3 tools/run_extension.py --limit 100000000000000 \
  --seed runs/seed.csv --output runs/extension_1e14 \
  --workers 4 --block 2097152 --audit-block 262144 \
  --cumulative-jumps --interval-audit --audit-chunk 4294967296
```

The seed must contain a complete, correct prefix. The generator checks CSV
structure and the final contact, then recomputes from just after its last term.
It does **not** fully verify the seed. The output includes the seed terms, so a
completed output is a self-contained prefix suitable for the full auditor.

For direct generator calls, the positional argument after the seed controls
histogram workers (default 1), and the optional `--jump` flag follows it.
Use `-` instead of a seed filename to start from scratch with multiple workers. Only pair preparation
is parallel; benchmark worker counts and block sizes on the chosen hardware.

`SIGINT`/`SIGTERM` request a stop after the current block or jump (exit code 3).
Progress JSON and flushed CSV are saved at the next such boundary after 30 seconds.
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

- `src/`: optimized generator and two independent auditors with strict input checks.
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
