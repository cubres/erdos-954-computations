# Algorithms and correctness

Let `rho(x)` count positive unordered pairs with sum exactly `x`, including
diagonal pairs. Just before processing `x`, the running surplus is `E(x-1)`.

- If both the surplus and `rho(x)` are zero, insert `x`. Its zero-pair contributes
  one to `R(x)`, so the new surplus remains zero.
- Otherwise, do not insert; the surplus becomes `E(x-1) + rho(x) - 1`.

Inductively the surplus is nonnegative. This implements the greedy definition:
an insertion happens precisely where the currently available pair count would
otherwise first fall below the argument. Future terms cannot affect an earlier
pair count, since every term is positive apart from the fixed initial zero.

## Segmented pair sums

For each interval `[left,right)`, build a histogram of sums of already known
positive terms. Restrict pairs to indices `i<=j`. Two monotone pointers delimit
the partner indices whose sums fall in the interval. When a new term `x` is
inserted, immediately add its pairs with all known terms (including itself)
whose sums remain in this interval. Future intervals reconstruct their own
histograms from the enlarged term list.

## Exact bulk step

Suppose the surplus before an interval of length `h` is at least `h`.
Since every arrival is nonnegative, the surplus before the interval's last
position is at least 1. No term can be inserted anywhere in the interval.
Consequently its entire effect is exactly

`new_surplus = old_surplus - h + sum(arrivals_in_interval)`.

The optimized generator applies this with
`h=min(current_surplus, positions_remaining_in_block)` whenever the surplus
is at least 1024. That threshold only selects a faster code path. Small surplus
positions use the original one-step rule. This changes neither the sequence nor
the cumulative count; it does skip intermediate error statistics, which the
separate auditor recovers.

The one-byte histogram saves memory traffic. Every increment checks for overflow
before changing the cell. If the bound 255 is reached, generation fails rather
than producing wrapped counts. All value arithmetic is unsigned 64-bit, with
an input cap of 10¹⁵ and explicit cumulative/error overflow checks where needed.

## Independent audit

The audit uses the complete final term list and a 32-bit histogram. One initial
binary search skips terms too large to contribute to the block. For row `i`,
two moving pointers delimit partners `j>=i` satisfying
`left <= a[i]+a[j] < right`. As `a[i]` increases, both value thresholds decrease;
the pointers move backward, with the lower bound clipped at `i` to retain
unordered counting and include each diagonal once. Range setup takes a linear
number of pointer steps per block, plus the initial search and pair enumeration.

At the start of each block the auditor independently computes `R(left-1)`
using a two-pointer cumulative pair count. It then visits
every integer, checking the surplus, required insertions, and forbidden
insertions. Blocks can be assigned to separate threads; none imports running
surplus state from the generator or from another audit block.

The auditor shares the mathematical definition, not the bulk step or online
insertion state. It is still software verification, not a formally checked proof
of the implementation. Small tests also use a direct Python definition that
recounts all pairs at every argument. Histogram tests compare against direct
pair enumeration on all subsets of `{1,...,9}` and every interval with integer
endpoints from 1 through 21, plus boundary cases near 10¹⁵: 107,622 comparisons.
The historical binary-search auditor remains in `reference/` for reproduction
and separate comparisons.

## Costs and limits

The generator and exhaustive auditor enumerate pair arrivals individually. Near the measured endpoint
there is approximately one pair arrival per integer on average. The bulk step
reduces scanning overhead but does not remove this main scaling cost.
Rebuilding partner ranges introduces additional work proportional to the term
count per block. Small blocks trade better cache locality for more repeated
setup. With multiple generator workers, each thread fills a disjoint subinterval
of the histogram using the same immutable known prefix. All workers join before
the sequential insertion phase begins. This parallelizes pair preparation, but
repeats some pointer setup per worker, so benchmark worker and block counts.
The final-list auditor parallelizes complete independently initialized blocks.

The alternative [interval auditor](interval-audit.md) can avoid both the
histogram and integer scan on regions certified by exact cumulative pair
counts. It retains complete coverage and recounts the same error statistics;
its advantage depends on the error profile and chosen leaf size.

Historical reference programs are preserved for provenance and have fewer input
guards. Their gap-area accumulator is 64-bit. Use them to reproduce the published
10¹² run, not as an unchecked arbitrary-range implementation.
