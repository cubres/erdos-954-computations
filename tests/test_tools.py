import importlib.util
import json
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("query", ROOT / "tools/query.py")
query = importlib.util.module_from_spec(spec)
spec.loader.exec_module(query)


class ToolTests(unittest.TestCase):
    def test_count_matches_direct_unordered_pairs(self):
        a = [1, 3, 5, 9, 13, 17, 24, 31, 38, 45]
        with_zero = [0] + a
        for x in range(100):
            expected = sum(with_zero[i] + with_zero[j] <= x
                           for j in range(1, len(with_zero)) for i in range(j + 1))
            self.assertEqual(query.count(a, x), expected)

    def test_pipeline_reaches_audited_and_wont_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            p = pathlib.Path(directory)
            seed = p / "seed.csv"
            seed.write_text("index,value\n1,1\n")
            cmd = ["python3", str(ROOT / "tools/run_extension.py"), "--limit", "10000",
                   "--seed", str(seed), "--output", str(p / "run"),
                   "--workers", "2", "--block", "8192", "--audit-block", "4096"]
            first = subprocess.run(cmd, text=True, capture_output=True)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            state = json.loads((p / "run/pipeline.json").read_text())
            self.assertEqual(state["stage"], "AUDITED")
            self.assertEqual(len(state["terms_sha256"]), 64)
            second = subprocess.run(cmd, text=True, capture_output=True)
            self.assertNotEqual(second.returncode, 0)


if __name__ == "__main__":
    unittest.main()
