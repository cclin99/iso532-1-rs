"""Audit the legacy binary-float closest-variant predicate against decimal CSV units."""
from pathlib import Path
import re,json
import numpy as np
R=Path.cwd();O=Path(__file__).resolve().parent;T=R/'tmp/verification-f03-filter-independent'
refs=np.load(T/'workbook-refs.npz',allow_pickle=True)['refs'].item()
tot=np.zeros(4,dtype=int); corrected=np.zeros(4,dtype=int); mismatches=[];per={}
for s in range(6,26):
    vals={}
    for v in ['022','024']:
        txt=(T/f'cli{v}'/f'sig{s}'/'Loudness.csv').read_text()
        a=np.array([[float(x) for x in l.split(';')] for l in txt.splitlines() if re.match(r'^\d',l)])
        ix=np.searchsorted(np.rint(a[:,0]*10000).astype(int),refs[s]['time_ticks'])
        vals[v]=a[ix,1]
    r=np.array(refs[s]['n']);a=vals['022'];b=vals['024']
    mask=np.abs(a-b)>=2e-4-1e-9
    d22=np.abs(a-r);d24=np.abs(b-r)
    counts=np.array([mask.sum(),(mask&(d22<5e-5)).sum(),(mask&(d24<5e-5)).sum(),(mask&(d22<d24)).sum()]);tot+=counts
    ai=np.rint(a*10000).astype(int);bi=np.rint(b*10000).astype(int);ri=np.rint(r*10000).astype(int)
    e22=np.abs(ai-ri);e24=np.abs(bi-ri);m=np.abs(ai-bi)>=2
    assert np.array_equal(mask,m)
    ci=np.array([m.sum(),(m&(e22==0)).sum(),(m&(e24==0)).sum(),(m&(e22<e24)).sum()]);corrected+=ci
    ids=np.flatnonzero(mask&((d22<d24)!=(e22<e24)))
    per[s]={'legacy_counts':counts.tolist(),'integer_counts':ci.tolist(),'predicate_disagreements':len(ids)}
    for i in ids:
        mismatches.append({'signal':s,'time_s':refs[s]['time_ticks'][i]/10000,'workbook':float(r[i]),'v022':float(a[i]),'v024':float(b[i]),
            'float_error022':float(d22[i]),'float_error024':float(d24[i]),'integer_error022':int(e22[i]),'integer_error024':int(e24[i])})
out={'count_order':['decisive','equal022','equal024','closer022'],'legacy_totals':tot.tolist(),'integer_totals':corrected.tolist(),
     'all_disagreements_are_decimal_ties':all(x['integer_error022']==x['integer_error024'] for x in mismatches),
     'disagreements':mismatches,'per_signal':per}
(O/'rounding-audit.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print('Legacy:',tot.tolist(),'Decimal:',corrected.tolist(),'misclassified ties:',len(mismatches))
