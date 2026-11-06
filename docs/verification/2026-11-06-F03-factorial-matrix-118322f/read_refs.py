from pathlib import Path
import re,json,hashlib
import openpyxl
R=Path.cwd();O=Path(__file__).resolve().parent;T=R/'tmp/verification-f03-factorial-matrix';OFF=R/'tmp/c01-material/official'
refs={}
for p in OFF.rglob('*.xlsx'):
 for sh in openpyxl.load_workbook(p,data_only=True,read_only=True):
  s=int(re.search(r'\d+',sh.title)[0]);rr=list(sh.values)
  if s<=5:refs[s]={'n':[float(rr[7][1])],'specific':[[float(r[6])] for r in rr[7:247]],'time':[0.]}
  else:
   rows=[r for r in rr[10:] if isinstance(r[0],(int,float)) and isinstance(r[1],(int,float))]
   refs[s]={'n':[r[1] for r in rows],'time':[r[0] for r in rows]}
   if s<=13:refs[s].update(specific=[[r[11] for r in rows]],bark=float(str(rr[8][11]).split()[1].replace(',','.')))
p=T/'refs.json';p.write_text(json.dumps(refs));(O/'reference-extraction.json').write_text(json.dumps({'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'signals':list(sorted(refs)),'fresh_read_from_frozen_official_workbooks':True},indent=2))
print('Fresh workbook cell extraction complete')
