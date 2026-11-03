"""Artifact consistency audit, not a second numerical acceptance round."""
import csv, hashlib, json, re, struct
from pathlib import Path
p=Path(__file__).resolve().parent
r=json.loads((p/'results.json').read_text(encoding='utf8'));pairs=0
def bits(x):return struct.pack('>d',float(x)).hex()
for s in r['signals']:
    values=[s['total']]+s['specific']
    rows=list(csv.DictReader((p/f"signal-{s['signal']}-target.csv").open(encoding='utf8',newline='')))
    assert len(rows)==len(values)==241
    for v,row in zip(values,rows):
        for side in ['C','Rust']:
            assert bits(v[side]['decimal17'])==v[side]['bits']==row[side+'_binary64_hex']
            assert row[side+'_decimal17']==v[side]['decimal17']
        assert abs(float(v['C']['decimal17'])-float(v['Rust']['decimal17']))==v['abs_diff']==float(row['abs_difference_decimal17'])
        pairs+=1
    assert max(v['abs_diff'] for v in s['specific'])==s['comparison']['max_specific_abs_diff']
    assert s['comparison']['verdict']=='WITHIN TOLERANCE'
    assert s['comparator_negative_control']['passed'] and s['comparator_negative_control']['result']['first_failure']=='specific[137]'
assert pairs==964
start=json.loads((p/'run-start.json').read_text(encoding='utf8'))
for name,h in start['design_sha256'].items():assert hashlib.sha256((p/name).read_bytes()).hexdigest()==h
def tables(name):return re.findall(r'(?:^\|.*\n)+',(p/name).read_text(encoding='utf8'),re.M)
assert tables('report.md')==tables('report.en.md')
def data_rows(name):return [t.splitlines()[2:] for t in tables(name)]
assert data_rows('experiment-design.md')==data_rows('experiment-design.en.md')
assert r['numeric_gap_closure_recommended'] is False
assert sum(r['gates'].values())==9 and len(r['gates'])==10
assert len(r['boundaries'])==8 and all(x['passed'] for x in r['boundaries'])
supported={'.md','.json','.txt','.log','.ps1','.py','.csv','.yml','.yaml','.toml','.sh'}
files=[x for x in p.rglob('*') if x.is_file() and x.name not in {'artifact-audit.json','delivery-integrity.json'}]
unsupported=[];utf8=[]
for f in files:
    f.read_bytes().decode('utf8',errors='strict');utf8.append(str(f.relative_to(p)))
    if f.suffix.lower() not in supported:unsupported.append(str(f.relative_to(p)))
assert not unsupported
result={'purpose':'delivery artifact consistency only; not independent numerical re-execution',
 'decimal_bits_CSV_pairs_checked':pairs,'all_decimal_bits_errors_CSV_consistent':True,
 'preregistered_design_hashes_unchanged':True,'bilingual_report_tables_identical':True,
 'bilingual_design_tables_identical':True,'final_gate_counts':{'passed':9,'failed':1},
 'boundary_passed_count':8,'closure_recommended':False,'utf8_files_checked':utf8,
 'unsupported_extensions':unsupported,'non_UTF8_files':[],'passed':True}
(p/'artifact-audit.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf8',newline='\n')
print(json.dumps({k:v for k,v in result.items() if k!='utf8_files_checked'},ensure_ascii=False))
