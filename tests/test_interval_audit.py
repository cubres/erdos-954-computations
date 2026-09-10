import csv
import json
import pathlib
import subprocess
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
FIELDS=("status","limit","terms","R_limit","E_limit","maximum_error",
        "first_maximizer","last_maximizer","zero_error_positions",
        "all_contacts_checked","all_greedy_decisions_checked")


def call(*args):
    return subprocess.run([str(a) for a in args],capture_output=True,text=True)


def direct_sequence(limit):
    a=[0]
    for x in range(1,limit+1):
        count=sum(a[i]+a[j]<=x for j in range(1,len(a)) for i in range(j+1))
        if count<x:
            a.append(x)
    return a[1:]


def direct_metrics(a,limit):
    values=[0]+a
    e=[sum(values[i]+values[j]<=x for j in range(1,len(values))
           for i in range(j+1))-x for x in range(1,limit+1)]
    m=max(e)
    return dict(zip(FIELDS,("PASS",limit,len(a),limit+e[-1],e[-1],m,
                           e.index(m)+1,limit-e[::-1].index(m),e.count(0),True,True)))


class IntervalAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.p=pathlib.Path(self.temp.name)
        self.counter=0

    def tearDown(self):
        self.temp.cleanup()

    def write(self,name,a):
        path=self.p/name
        path.write_text("index,value\n"+"".join(f"{i},{v}\n" for i,v in enumerate(a,1)))
        return path

    def audit(self,path,limit,workers=2,leaf=7,chunk=31,ok=True,
              decisions_only=False,start=None):
        self.counter+=1
        out=self.p/f"audit-{self.counter}.json"
        options=[]
        if decisions_only:
            options.append("--decisions-only")
        if start is not None:
            options.extend(("--start",start))
        result=call(ROOT/"build/audit_intervals",path,limit,out,workers,leaf,chunk,*options)
        self.assertEqual(result.returncode==0,ok,result.stdout+result.stderr)
        if not ok:
            self.assertFalse(out.exists())
            return
        data=json.loads(out.read_text())
        self.assertEqual(data["positions_scanned"]+data["positions_certified_by_enclosure"],
                         limit-(start or 0))
        return data

    def test_decisions_only_and_range_boundaries(self):
        limit=500
        a=direct_sequence(limit)
        path=self.write("valid.csv",a)
        expected=direct_metrics(a,limit)
        for start in (None,0,1,2,3,6,7,13,24,25,33,47,499):
            for workers,leaf,chunk in ((1,1,17),(3,7,31)):
                with self.subTest(start=start,workers=workers):
                    got=self.audit(path,limit,workers,leaf,chunk,
                                   decisions_only=True,start=start)
                    lo=start or 0
                    self.assertFalse(got["maximum_evaluated"])
                    for field in ("maximum_error","first_maximizer","last_maximizer"):
                        self.assertNotIn(field,got)
                    self.assertEqual(got["prefix_assumed_valid_through"],lo)
                    self.assertEqual(got["all_greedy_decisions_checked"],lo==0)
                    self.assertEqual(got["all_contacts_checked"],lo==0)
                    self.assertTrue(got["all_range_greedy_decisions_checked"])
                    self.assertTrue(got["all_range_contacts_checked"])
                    self.assertEqual(got["range_terms_checked"],sum(v>lo for v in a))
                    for field in ("terms","R_limit","E_limit"):
                        self.assertEqual(got[field],expected[field])
                    values=[0]+a
                    zeros=sum(sum(values[i]+values[j]<=x
                                  for j in range(1,len(values)) for i in range(j+1))==x
                              for x in range(lo+1,limit+1))
                    self.assertEqual(got["range_zero_error_positions"],zeros)
                    if lo:
                        self.assertNotIn("zero_error_positions",got)
                    else:
                        self.assertEqual(got["zero_error_positions"],zeros)

    def test_every_suffix_candidate_with_an_audited_prefix(self):
        limit=8
        correct=direct_sequence(limit)
        for start in (1,3,6,7):
            prefix=[v for v in correct if v<=start]
            for mask in range(1<<(limit-start)):
                a=prefix+[v for v in range(start+1,limit+1)
                          if mask&(1<<(v-start-1))]
                self.audit(self.write("candidate.csv",a),limit,1,2,3,
                           decisions_only=True,start=start,ok=a==correct)

    def test_direct_definition_and_metrics(self):
        for limit in (1,2,3,7,33,500):
            a=direct_sequence(limit)
            path=self.write("valid.csv",a)
            expected=direct_metrics(a,limit)
            for workers,leaf,chunk in ((1,1,17),(2,7,31),(4,1000,10000)):
                with self.subTest(limit=limit,workers=workers):
                    got=self.audit(path,limit,workers,leaf,chunk)
                    self.assertEqual({k:got[k] for k in FIELDS},expected)

    def test_every_candidate_set_through_eight(self):
        correct=direct_sequence(8)
        for mask in range(1<<7):
            a=[1]+[v for v in range(2,9) if mask&(1<<(v-2))]
            self.audit(self.write("candidate.csv",a),8,1,3,7,ok=a==correct)

    def test_pruning_matches_exhaustive_and_rejects_corruption(self):
        limit=100000000
        prefix=self.p/"generated"
        generated=call(ROOT/"build/generate",limit,prefix,1048576)
        self.assertEqual(generated.returncode,0,generated.stderr)
        path=pathlib.Path(str(prefix)+"_terms.csv")
        out=self.p/"exhaustive.json"
        result=call(ROOT/"build/audit",path,limit,out,2,1048576)
        self.assertEqual(result.returncode,0,result.stderr)
        expected=json.loads(out.read_text())
        got=self.audit(path,limit,2,4096,67108864)
        self.assertGreater(got["positions_certified_by_enclosure"],0)
        self.assertGreater(got["positions_scanned"],0)
        self.assertEqual({k:got[k] for k in FIELDS},{k:expected[k] for k in FIELDS})
        decisions=self.audit(path,limit,2,4096,67108864,decisions_only=True)
        self.assertGreater(decisions["positions_certified_by_enclosure"],0)
        self.assertGreater(decisions["positions_scanned"],0)
        for field in ("terms","R_limit","E_limit","zero_error_positions"):
            self.assertEqual(decisions[field],expected[field])
        with path.open() as stream:
            a=[int(row["value"]) for row in csv.DictReader(stream)]
        extra=90000000
        while extra in a:
            extra+=1
        for name,altered in (("missing",[v for v in a if v!=13]),
                             ("last",a[:-1]),("spurious",sorted(a+[extra])),
                             ("shifted",a[:-1]+[a[-1]+1])):
            self.audit(self.write(name+".csv",altered),limit,2,4096,67108864,ok=False)
            self.audit(self.write(name+".csv",altered),limit,2,4096,67108864,
                       decisions_only=True,ok=False)

    def test_invalid_inputs_and_no_overwrite(self):
        path=self.p/"bad.csv"
        for content in ("wrong\n1,1\n","index,value\n2,1\n","index,value\n1,-1\n",
                        "index,value\n1,1","index,value\n1,1\n2,1\n"):
            path.write_text(content)
            self.audit(path,100,ok=False)
        path=self.write("good.csv",direct_sequence(100))
        for workers,leaf,chunk in ((0,1,1),(257,1,1),(1,0,1),(1,1,0)):
            self.audit(path,100,workers,leaf,chunk,ok=False)
        out=self.p/"existing.json";out.write_text("preserve me\n")
        result=call(ROOT/"build/audit_intervals",path,100,out)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(out.read_text(),"preserve me\n")
        for options in (("--start","3"),("--decisions-only","--start","100"),
                        ("--decisions-only","--start","101"),("--start",),
                        ("--decisions-only","--start","-1"),("--unknown",),
                        ("--decisions-only","--decisions-only"),
                        ("--decisions-only","--start","1","--start","2")):
            unused=self.p/"invalid-options.json"
            result=call(ROOT/"build/audit_intervals",path,100,unused,*options)
            self.assertNotEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertFalse(unused.exists())


if __name__=="__main__":
    unittest.main()
