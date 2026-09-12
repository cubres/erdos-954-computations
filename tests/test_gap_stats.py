import gzip
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gap_stats", ROOT / "tools/gap_stats.py")
gap_stats = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gap_stats)


class GapStatsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = pathlib.Path(self.tmp.name) / "terms.csv"

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, values):
        raw = "index,value\n" + "".join(f"{index},{value}\n" for index, value in enumerate(values, 1))
        self.path.write_text(raw)
        return raw.encode()

    def assert_direct_summary(self, values, limit, through=None):
        self.write(values)
        actual = gap_stats.summarize(self.path, limit, through)
        cutoff = limit if through is None else through
        grouped = {}
        for p, q in zip(values, values[1:]):
            if q <= cutoff:
                power = 1
                while p >= power * 10:
                    power *= 10
                grouped.setdefault(power, []).append((p, q))
        self.assertEqual(actual["completed_gaps"], sum(map(len, grouped.values())))
        self.assertEqual(len(actual["decades"]), len(grouped))
        for item in actual["decades"]:
            pairs = grouped[item["left_at_least"]]
            lengths = [q - p for p, q in pairs]
            self.assertEqual(item["gaps"], len(pairs))
            self.assertEqual(item["sum_length"], sum(lengths))
            self.assertEqual(item["min_length"], min(lengths))
            self.assertEqual(item["max_length"], max(lengths))
            self.assertEqual(item["above_normalized_threshold"], [
                sum((q - p) ** 2 > threshold ** 2 * p for p, q in pairs)
                for threshold in range(1, 1025) if threshold & (threshold - 1) == 0])
        return actual

    def test_strict_threshold_equality_and_large_integers(self):
        # Square p makes each threshold exact; neighboring lengths check strictness.
        for root in (2, 10, 10 ** 10):
            for threshold in gap_stats.THRESHOLDS:
                for delta in (-1, 0, 1):
                    p = root ** 2
                    g = threshold * root + delta
                    with self.subTest(root=root, threshold=threshold, delta=delta):
                        actual = self.assert_direct_summary([1, p, p + g], p + g)
                        counts = actual["decades"][-1]["above_normalized_threshold"]
                        if root > 2:  # p has its own bin, away from the first gap.
                            self.assertEqual(counts[gap_stats.THRESHOLDS.index(threshold)], int(delta > 0))

    def test_decade_crossing_cutoff_and_unfinished_tail(self):
        values = [1, 4, 9, 10, 20, 25, 30, 100, 110]
        for cutoff in (0, 1, 8, 9, 10, 99, 100, 110, 200):
            self.assert_direct_summary(values, 200, cutoff)
        full = gap_stats.summarize(self.path, 200)
        self.assertEqual([item["gaps"] for item in full["decades"]], [3, 4, 1])
        self.assertEqual(full["completed_gaps"], len(values) - 1)

    def test_gzip_matches_csv_and_binds_uncompressed_bytes(self):
        raw = self.write([1, 3, 5, 9, 13, 17])
        zipped = self.path.with_suffix(".csv.gz")
        with gzip.open(zipped, "wb") as stream:
            stream.write(raw)
        plain = gap_stats.summarize(self.path, 20)
        compressed = gap_stats.summarize(zipped, 20)
        self.assertEqual(plain["decades"], compressed["decades"])
        for result in (plain, compressed):
            self.assertEqual(result["input"]["uncompressed_sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(result["input"]["uncompressed_bytes"], len(raw))
            self.assertFalse(result["independently_audited_by_this_tool"])

    def test_rejects_invalid_or_truncated_input_even_after_cutoff(self):
        invalid = [b"", b"index,value\n", b"index,value\n1,2\n",
                   b"index,value\n1,1\n3,3\n", b"index,value\n1,1\n2,1\n",
                   b"index,value\n1,1\n2,3", b"index,value\n1,1\n2,3,4\n",
                   b"index,value\n1,1\n2,-3\n", b"index,value\n1,1\n2,3.0\n"]
        for raw in invalid:
            self.path.write_bytes(raw)
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                gap_stats.summarize(self.path, 100, 1)
        self.write([1, 3])
        for limit, through in ((0, None), (2, None), (10, -1), (10, 11)):
            with self.subTest(limit=limit, through=through), self.assertRaises(ValueError):
                gap_stats.summarize(self.path, limit, through)

    def test_sample_matches_separate_direct_gap_count(self):
        sample = ROOT / "data/sample_1e6.csv"
        values = [int(line.split(",")[1]) for line in sample.read_text().splitlines()[1:]]
        expected = self.assert_direct_summary(values, 1_000_000)
        actual = gap_stats.summarize(sample, 1_000_000)
        self.assertEqual(actual["decades"], expected["decades"])
        self.assertEqual(actual["completed_gaps"], 1592)

    def test_cli_and_validation_error(self):
        self.write([1, 3, 5, 9])
        command = ["python3", str(ROOT / "tools/gap_stats.py"), str(self.path), "--limit", "10"]
        result = subprocess.run(command, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["completed_gaps"], 3)
        invalid = subprocess.run(command + ["--through", "11"], text=True, capture_output=True)
        self.assertNotEqual(invalid.returncode, 0)
        self.assertIn("through <= limit", invalid.stderr)


if __name__ == "__main__":
    unittest.main()
