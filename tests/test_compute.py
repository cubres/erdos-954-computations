import csv
import json
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def run(*args, ok=True):
    p = subprocess.run([str(x) for x in args], text=True, capture_output=True)
    if ok and p.returncode:
        raise AssertionError(p.stdout + p.stderr)
    return p


def terms(path):
    with open(path, newline="") as f:
        return [int(row["value"]) for row in csv.DictReader(f)]


def brute_force(limit):
    """Direct finite definition; no arrival histogram or running-error state."""
    a = [0]
    for x in range(1, limit + 1):
        count = sum(a[i] + a[j] <= x
                    for j in range(1, len(a)) for i in range(j + 1))
        if count < x:
            assert count == x - 1
            a.append(x)
    return a[1:]


class ComputeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def generate(self, name, limit, block, seed=None):
        prefix = self.p / name
        args = [ROOT / "build/generate", limit, prefix, block]
        if seed is not None:
            args.append(seed)
        run(*args)
        return pathlib.Path(str(prefix) + "_terms.csv")

    def audit(self, path, limit, workers=2, block=97, ok=True):
        out = self.p / (path.stem + f"-audit-{workers}-{block}.json")
        p = run(ROOT / "build/audit", path, limit, out, workers, block, ok=ok)
        return json.loads(out.read_text()) if p.returncode == 0 else p

    def test_direct_definition_and_block_boundaries(self):
        for limit in (1, 2, 3, 7, 33, 500):
            expected = brute_force(limit)
            for block in (1, 7, 64, 1024):
                with self.subTest(limit=limit, block=block):
                    path = self.generate(f"g{limit}-{block}", limit, block)
                    self.assertEqual(terms(path), expected)
                    audit = self.audit(path, limit)
                    self.assertEqual(audit["status"], "PASS")

    def test_bulk_step_against_reference(self):
        limit = 20_000_000
        ref = self.p / "ref"
        run(ROOT / "build/reference", limit, ref, 262144)
        expected = pathlib.Path(str(ref) + "_terms.csv").read_bytes()
        for block in (65536, 1048576):
            path = self.generate(f"bulk{block}", limit, block)
            self.assertEqual(path.read_bytes(), expected)
            s = json.loads(path.with_name(path.name.replace("_terms.csv", "_summary.json")).read_text())
            self.assertGreater(s["bulk_positions"], 0)
            audit = self.audit(path, limit, block=262144)
            self.assertEqual(s["E"], audit["E_limit"])

    def test_resume_matches_from_scratch(self):
        seed = self.generate("seed", 100003, 319)
        full = self.generate("full", 500000, 4096)
        resumed = self.generate("resumed", 500000, 12345, seed)
        self.assertEqual(full.read_bytes(), resumed.read_bytes())
        self.audit(resumed, 500000, 3, 8192)

    def test_parallel_generator(self):
        limit = 5000000
        single = self.generate("single", limit, 1048576)
        for workers in (2, 3, 4):
            prefix = self.p / f"parallel{workers}"
            run(ROOT / "build/generate", limit, prefix, 1048576, "-", workers)
            self.assertEqual(single.read_bytes(), pathlib.Path(str(prefix)+"_terms.csv").read_bytes())

    def test_graceful_stop_and_resume(self):
        seed = self.generate("stopseed", 1000, 97)
        prefix = self.p / "stopped"
        process = subprocess.Popen([str(ROOT / "build/generate"), "10000000000000",
                                    str(prefix), "4096", str(seed)],
                                   text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertIn("RUNNING", process.stdout.readline())
        process.terminate()
        stdout, stderr = process.communicate(timeout=15)
        self.assertEqual(process.returncode, 3, stdout + stderr)
        status = json.loads(pathlib.Path(str(prefix)+"_summary.json").read_text())
        self.assertEqual(status["status"], "STOPPED")
        target = status["processed_through"] + 1000
        resumed = self.generate("afterstop", target, 511, pathlib.Path(str(prefix)+"_terms.csv"))
        full = self.generate("stopfull", target, 1024)
        self.assertEqual(resumed.read_bytes(), full.read_bytes())
        self.audit(resumed, target, block=4096)

    def test_audit_rejects_missing_and_spurious_terms(self):
        path = self.generate("valid", 1000, 71)
        original = terms(path)
        for name, altered in (("missing", original[:5] + original[6:]),
                              ("spurious", sorted(original + [2]))):
            bad = self.p / f"{name}.csv"
            bad.write_text("index,value\n" + "".join(f"{i},{v}\n" for i, v in enumerate(altered, 1)))
            self.assertNotEqual(self.audit(bad, 1000, ok=False).returncode, 0)

    def test_rejects_malformed_inputs_and_existing_outputs(self):
        for content in ("wrong\n1,1\n", "index,value\n2,1\n", "index,value\n1,-1\n",
                        "index,value\n1,1", "index,value\n1,1\n2,1\n"):
            seed = self.p / "bad.csv"
            seed.write_text(content)
            self.assertNotEqual(run(ROOT / "build/generate", 100, self.p / "bad",
                                    32, seed, ok=False).returncode, 0)
            self.assertNotEqual(self.audit(seed, 100, ok=False).returncode, 0)
        good = self.generate("good", 100, 32)
        before = good.read_bytes()
        self.assertNotEqual(run(ROOT / "build/generate", 100, self.p / "good", 32, ok=False).returncode, 0)
        self.assertEqual(good.read_bytes(), before)
        self.assertNotEqual(run(ROOT / "build/generate", "-1", self.p / "negative", ok=False).returncode, 0)


if __name__ == "__main__":
    unittest.main()
