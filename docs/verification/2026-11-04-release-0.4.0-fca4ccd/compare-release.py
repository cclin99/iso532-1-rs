"""Compare release numeric tables with this round, allowing printed rounding only."""
from pathlib import Path
import json,re
R=Path.cwd();O=Path(__file__).resolve().parent;N=json.loads((O/'numeric-results.json').read_text());S=json.loads((O/'supplemental-release-numbers.json').read_text());text=(R/'tmp/acceptance-040-astra/candidate/docs/RELEASE-0.4.0-2026-11-04.zh-TW.md').read_text();rows=[]
def item(scope,name,claim,got):
 value=float(claim);digits=len(claim.split('e')[0].split('.')[-1]);exp=int(claim.split('e')[1]);tol=.5*10**(exp-digits);rows.append({'scope':scope,'name':name,'printed':claim,'measured':got,'rounding_half_unit':tol,'matches_printed_rounding':abs(got-value)<=tol})
for line in text.splitlines():
 parts=[x.strip() for x in line.split('|')]
 if len(parts)==6 and parts[1] in N['sequences']:
  e=N['sequences'][parts[1]]
  for label,c,g in [('N',parts[2],e['patched']['n']['max_abs']),('specific_new',parts[3],e['patched']['specific']['max_abs']),('specific_round1',parts[4],e['round1_vs_patched']['specific']['max_abs'])]:item('time_varying',parts[1]+':'+label,c,g)
for name,e in N['sequences'].items():
 if not name.startswith('annexb_c01'):continue
 signal=name.split('sig')[-1]
 line=next(x for x in text.splitlines() if x.startswith('| '+signal+' |'));parts=[p.strip().replace('−','-') for p in line.split('|')]
 item('tail',signal+':N',parts[2],e['patched']['tail_total_delta']);item('tail',signal+':specific',parts[3],e['patched']['tail_specific_max']);item('tail',signal+':official_delta',parts[4],e['official']['tail_total_delta'])
item('stationary','N','1.530e-5',max(e['stationary']['n']['max_abs'] for e in N['sequences'].values() if 'stationary' in e));item('stationary','specific_new','1.500e-4',max(e['stationary']['specific']['max_abs'] for e in N['sequences'].values() if 'stationary' in e));item('stationary','specific_round1','7.960e-3',max(e['specific'] for e in S.values() if 'specific' in e))
(O/'release-numeric-comparison.json').write_text(json.dumps({'rows':rows,'all_rounding_matches':all(x['matches_printed_rounding'] for x in rows),'historical_claims':'Historical RED execution and old Linux run are not rerun as historical events. Candidate tests, Round1 output and fresh Linux gates provide current evidence; the 507-frame assertion is exercised by the candidate unit test.'},indent=2));print(len(rows),[x for x in rows if not x['matches_printed_rounding']])
