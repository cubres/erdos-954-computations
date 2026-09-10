# Independent audit by interval enclosures

The interval auditor accepts a final positive-term CSV. It computes cumulative
pair counts directly from that list and never imports the generator's surplus
or arrival table. It certifies the same finite properties as the exhaustive
auditor: every greedy decision, every contact, the endpoint count, the number
of zero-error positions, and the global maximum with its first and last positions.

This is a mathematical justification of the verification algorithm, not a
proof-assistant certification or an asymptotic result about the sequence.

## The interval certificate

For an integer interval [l,r], compute L=R(l-1) and U=R(r) exactly.
The representation count is nondecreasing for any supplied set of positive terms,
including an incorrect candidate. Therefore, for every integer t in [l,r],

~~~math
L-r \le E(t) \le U-l.
~~~

Maintain M as an error value already witnessed by an exact pair count.
The auditor certifies an entire interval without a histogram when

~~~math
L>r,\qquad U-l<M,
~~~

and the supplied list has no term in [l,r]. These strict inequalities prove
that every position has positive error and that none attains the eventual
global maximum. Consequently the interval contributes no contacts, no
zero-error positions, and no maximizing positions.

The test uses monotonicity of R, not monotonicity of E. Equality in either
comparison is insufficient for pruning: it may conceal a zero or a maximizer.

## Why this checks every greedy decision

At an unlisted integer t, the exact identity is

~~~math
E(t)=E(t-1)+\rho(t)-1,
~~~

where rho counts positive unordered arrivals. If the greedy rule required an
insertion there, both terms on the right before subtracting one would vanish,
giving E(t)=-1. Positive error throughout a certified interval rules this out.
An input term inside such an interval is rejected because its contact error
would be positive.

All intervals that cannot be certified are bisected. Once a leaf is sufficiently
short, the auditor rebuilds its complete positive-pair histogram and checks
every integer, including both presence and absence of required insertions.
The initial value R(l-1) and final value R(r) are independently recounted;
the histogram's endpoint must agree.

These leaves and certified intervals partition every integer from 1 through
the declared limit. The final report checks that their lengths sum to the limit
and that every input term was checked in a leaf.

## Why the maximum and zero count are exact

The initial M comes from up to 64 exact cumulative-count queries. These sample
values are only witnessed lower bounds; sampling is not used to certify
the global maximum. Scanned leaves can increase M.

Every pruned position has error strictly below a previously witnessed value,
so it cannot be a true global maximizer. Thus every maximizing position must
be scanned, including a sampled maximizer if it remains maximal. The final
maximum and its first and last positions come from the scanned leaves and
are checked against the shared witnessed maximum.

Every pruned position also has strictly positive error. Hence all zero-error
positions are scanned and counted exactly. Different thread schedules can
change the pruning statistics, but not these mathematical results.

## Run and tune

~~~sh
make
./build/audit_intervals TERM_CSV LIMIT OUTPUT_JSON [WORKERS] [LEAF] [CHUNK]
~~~

Defaults are 3 workers, leaf size 1,048,576, and chunk size 1,073,741,824.
The supported limit is 1 through 10^15. Output files must not already exist.

Workers process disjoint top-level chunks. Each worker uses a histogram of
at most LEAF 32-bit entries. Smaller leaves permit finer certificates but
increase the number of cumulative pair queries, each linear in the relevant
term count. A large leaf can prevent pruning entirely on a small-error prefix.
CHUNK controls task size and the top of the bisection tree; it need not fit
in a histogram.

For example, a small-range check with finer leaves is:

~~~sh
./build/audit_intervals runs/example_terms.csv 100000000 runs/interval_audit.json 2 4096 67108864
~~~

The report has the exhaustive auditor's mathematical fields plus:

- positions_scanned and positions_certified_by_enclosure, whose sum is LIMIT;
- pruned_intervals and histogram_leaves;
- interval_count_queries and sample_queries;
- workers, leaf, chunk, and seconds.

The method does not assume a conjectural upper bound for E or use a supplied
maximum. If the interval tests fail, it falls back to complete leaf scans.
There is no uniform runtime improvement guarantee.

The existing extension pipeline still invokes the exhaustive auditor.
The interval auditor is a separately selectable verification method.
