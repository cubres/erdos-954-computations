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

    def audit(self,path,limit,workers=2,leaf=7,chunk=31,ok=True):
        self.counter+=1
        out=self.p/f"audit-{self.counter}.json"
        result=call(ROOT/"build/audit_intervals",path,limit,out,workers,leaf,chunk)
        self.assertEqual(result.returncode==0,ok,result.stdout+result.stderr)
        if not ok:
            self.assertFalse(out.exists())
            return
        data=json.loads(out.read_text())
        self.assertEqual(data["positions_scanned"]+data["positions_certified_by_enclosure"],limit)
        return data

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
        with path.open() as stream:
            a=[int(row["value"]) for row in csv.DictReader(stream)]
        extra=90000000
        while extra in a:
            extra+=1
        for name,altered in (("missing",[v for v in a if v!=13]),
                             ("last",a[:-1]),("spurious",sorted(a+[extra])),
                             ("shifted",a[:-1]+[a[-1]+1])):
            self.audit(self.write(name+".csv",altered),limit,2,4096,67108864,ok=False)

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


if __name__=="__main__":
    unittest.main()
