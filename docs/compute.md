# Compute options and reproducible sizing

Checked 2026-09-10. **Only 10¹² is currently released as fully audited.**
Hardware estimates below are planning estimates, not completed computations.

## What limits this workload

The generator enumerates positive pair arrivals and maintains a sequential greedy
state. It now parallelizes the pair histogram, while bulk summation reduces
sequential scanning. The independent final-list auditor also uses multiple cores.
There is no GPU implementation in this repository. Renting a GPU by itself will
not accelerate these C++ executables.

RAM is manageable: an illustrative extrapolation of the observed term count
gives roughly 50 million terms near 10¹⁵, around 400 MB for the packed term vector.
That count extrapolation is not a proved asymptotic. Histograms and per-worker
audit buffers add memory; 8–16 GB suffices for the documented configurations.
Runtime and memory/cache bandwidth, rather than dataset storage, are the main
obstacles. More workers can repeat more range-setup work; benchmark before renting
a large machine.

## Measurements on the development machine

Intel Core i5-7400, 4 cores at 3.00 GHz, 8 GiB RAM, C++17 with `-O3`.

| Run | Elapsed time |
| --- | ---: |
| Historical generator from 0 through 10¹² | 7937.69 s |
| Historical full audit through 10¹², 4 workers | 3857.90 s |
| Original generator through 10⁹, current short benchmark | 12.9648 s |
| Initial bulk/byte generator through 10⁹ | 4.41102 s |
| Current generator near 10¹², 1 worker, block 2²⁵ | 15.9019 s |
| Current generator near 10¹², 2 workers, block 2²⁵ | 8.55684 s |
| Current generator near 10¹², 4 workers, block 2²⁵ | 7.21634 s |
| Current generator near 10¹², 4 workers, block 2²⁷ | 5.12627 s |

Each near-10¹² run resumes from the last term in the released prefix,
999090255890, and processes through 1002000000000: exactly 2909744110 positions.
All four current-generator configurations produced byte-identical term lists.
Their final endpoint recounts passed. These tiny extension benchmarks are **not
independent full audits of the new suffix**. The seed CSV parse/copy and histogram
allocation precede the generator's internal timer. Full pipeline costs include
those operations, logging, compression, and the separate audit.

At the fastest observed local marginal rate (about 568 million positions/second),
the remaining interval to 10¹³ would take about 4.4 hours to generate **if that
rate held**. A full audit adds substantial time. The same flat-rate extrapolation
to 10¹⁵ is about 20.4 days of generation alone. Neither is an ETA: term counts,
setup cost, block sizes, machine contention, and thermal conditions change.
The short benchmark is enough to justify a 10¹³ trial, not a promise of a cheap
or fast 10¹⁵ run.

## Online options

| Option | Current offer / limitation | Fit for this computation |
| --- | --- | --- |
| Google Cloud Free Trial | $300 credit for 90 days for eligible new users; payment-method verification; trial quotas cannot be increased | Best free-credit candidate for benchmarking a persistent CPU VM, subject to the account's actual quotas |
| Oracle Always Free | Current detailed documentation lists 1500 A1 OCPU-hours and 9000 GB-hours/month, equivalent to 2 OCPUs and 12 GB; capacity may be unavailable | Useful free sustained compute if provisionable, but not a large CPU speedup by itself |
| Colab free | Dynamic, unguaranteed resources; sessions at most 12 hours | Useful interactive experiments; unreliable for this entire long run |
| Netcup RS 1000 G12 | 4 dedicated cores, 8 GB; €12.79/month on the displayed annual contract, with a +€2.59/month option for a one-month term (prices shown include 19% German VAT) | Lower-cost paid candidate; confirm local VAT, term, and actual performance before purchase |
| Hetzner dedicated / auction | AX42-1 listed at €97.30/month plus €49 setup, excluding VAT and IPv4; limited AX41-1-LTD at €57.30/month and €0 setup, subject to availability | Candidate for sustained CPU work after a benchmark; auction hardware and offers vary |
| Hetzner CCX33 | 8 dedicated vCPUs, 32 GB; Germany/Finland €0.2219/hour, €138.49/month cap, excluding VAT and IPv4 | Flexible short benchmark; availability must be checked |
| AWS EC2 Spot | Advertised savings up to 90% off on-demand; instances can be interrupted | Potential value after benchmarking, with persistent prefixes and restart procedures; no fixed price assumed |

Sources: [Google trial conditions](https://docs.cloud.google.com/free/docs/free-cloud-features),
[Oracle detailed resource limits](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm),
[Colab FAQ](https://research.google.com/colaboratory/faq.html),
[Netcup offer and contract options](https://www.netcup.com/en/server/root-server/rs-1000-g12-ip-iv-12m),
[Hetzner June 2026 price schedule](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/),
[Hetzner CCX specifications](https://www.hetzner.com/cloud/general-purpose/),
[AWS Spot guidance](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-best-practices.html).
Provider specifications, availability, and prices can change; confirm the final
quote before provisioning. No cloud performance measurements are claimed here.

For example, at the quoted CCX33 hourly rate, a 24-hour rental is €5.33 and a
seven-day rental is €37.28 before tax, IPv4, and other charges. Those are rental
costs, **not estimates that either duration reaches 10¹⁵**.

## Practical run protocol

1. Build and run `make test` on the target machine.
2. Download and checksum the released prefix with `tools/fetch_data.py`.
3. Benchmark at least a few billion positions near the current endpoint, varying
   workers and block size. Do not extrapolate a tiny run from zero alone.
4. Extend to 10¹³ and independently audit it. Record hashes, commands, source
   commit, and hardware. Use that larger run to revise the 10¹⁵ budget.
5. Keep persistent backups. A process can resume from a complete CSV prefix;
   cloud VM disks or notebook files may disappear on termination.

The following runs generation and then automatically starts a **full** audit.
The output directory must not already exist. It records logs and `pipeline.json`;
only stage `AUDITED` means both programs completed successfully.

```sh
python3 tools/run_extension.py --limit 10000000000000 \
  --seed runs/seed.csv --output runs/extension \
  --workers 4 --block 134217728 --audit-block 33554432
```

The wrapper does not provision servers, incur cloud charges, or publish results.

For the free-credit option, see the [prepared one-hour Google Cloud benchmark](google-cloud-trial.md).
