# Google Cloud trial: one-hour CPU benchmark

This is a prepared benchmark plan, not a claim that a VM has been provisioned or
that 10¹⁵ has been computed. Checked 2026-09-10.

## Eligibility and quota

Eligible new users receive $300 credit for 90 days. Google requires the account
holder to complete identity and payment-method verification. A free-trial billing
account stops when credit or time expires; upgrading it to paid billing changes
that arrangement. See the [official trial conditions](https://docs.cloud.google.com/free/docs/free-cloud-features).

Google's [Dataflow quota documentation](https://docs.cloud.google.com/dataflow/quotas)
describes an eight-core limit for free-trial projects. Actual availability must
be read from the project's Compute Engine quotas, including per-machine-family
and regional quotas. Do not assume the trial grants a 64-core machine.

Read-only checks from an authenticated Cloud Shell or local `gcloud` installation:

```sh
gcloud compute project-info describe --project YOUR_PROJECT_ID --format=json
gcloud compute regions describe us-central1 --project YOUR_PROJECT_ID --format=json
```

These commands follow [Google's quota inspection guide](https://docs.cloud.google.com/compute/quotas-limits).
A project, active trial billing, and Compute Engine API access are prerequisites.

## Proposed benchmark

- One `n2d-highcpu-8` VM: 8 vCPUs, 8 GiB RAM, in an available `us-central1` zone.
  If that family has no quota, assess an allowed equivalent before creating it.
- Debian 12; one 20 GB standard persistent boot disk; no GPU.
- Maximum runtime one hour, automatic **STOP**, automatic restart disabled.
- Confirm the console's current regional quote and that trial credit covers it.
  At an illustrative $0.25/VM-hour, the CPU test uses about $0.25 of credit;
  disk, IPv4, and transfer are additional. This is a sizing example, not a quote.
- Build, test, fetch the released prefix, and compare 1/2/4/8 workers at block
  sizes 2²⁵ and 2²⁷. Keep exact output hashes and the actual CPU model from `lscpu`.
- Retrieve results, then delete the test VM and its boot disk. Stopped disks remain
  billable; stopping the CPU is not full resource cleanup.

The [VM creation reference](https://docs.cloud.google.com/sdk/gcloud/reference/compute/instances/create)
documents `--max-run-duration=3600s`, `--instance-termination-action=STOP`, and
`--no-restart-on-failure`. Apply these at creation; a terminal timeout alone does
not enforce a cloud spending limit.

## Commands inside the benchmark VM

After the VM is authorized and created, install the compiler and standard tools:

```sh
sudo apt-get update
sudo apt-get install -y build-essential git python3 gzip
git clone https://github.com/cubres/erdos-954-computations.git
cd erdos-954-computations
git rev-parse HEAD
lscpu
make test
python3 tools/fetch_data.py --terms-only --output runs/data
gzip -dc runs/data/terms_1e12.csv.gz > runs/seed.csv
python3 tools/benchmark.py --seed runs/seed.csv --limit 1010000000000 \
  --output runs/cloud-benchmark --workers 1 2 4 8 --blocks 33554432 134217728
```

The script checks that every configuration produces an identical term list.
It records both internal computation time and wall time including startup.
This is a performance benchmark with endpoint checks, not a full audit of the
new suffix. Extend further only after comparing measured throughput and the
separate audit cost against the remaining credit.

At an assumed sustained rate of one billion positions/second, generation through
10¹⁵ would still take about 11.6 days; at two billion/second, about 5.8 days.
Those rates have not been measured on a cloud VM. Audit time is additional, and
throughput may decline as the term list grows. The local 10¹³ run is the next
larger measurement needed for an informed decision.
