from pathlib import Path
import subprocess,json,numpy as np,re
R=Path.cwd();O=R/'docs/verification/2026-11-04-release-0.4.0-fca4ccd';W=R/'tmp/acceptance-040-astra/numeric';B=R/'tmp/acceptance-040-astra';r={}
for p in sorted((B/'candidate/data/golden-c').glob('*/zwst_levels.bin')):
 d=W/'old-stationary'/p.parent.name;subprocess.run([str(W/'round1/target/release/acceptance-numeric.exe'),'levels',str(p),str(d)],check=True);n=np.fromfile(d/'n.bin','<f8');s=np.fromfile(d/'s.bin','<f8');cn=np.fromfile(p.parent/'zwst_total.bin','<f8');cs=np.fromfile(p.parent/'zwst_specific.bin','<f8');r[p.parent.name]={'N':float(max(abs(n-cn))),'specific':float(max(abs(s-cs)))}
d=W/'old-single';subprocess.run([str(W/'round1/target/release/acceptance-numeric.exe'),'slope',str(W/'SIG18_FRAME1564.bin'),str(d)],check=True);n=np.fromfile(d/'n.bin','<f8');s=np.fromfile(d/'s.bin','<f8');r['sig18_round1']={'N':float(n[0]),'N_bits':f'{n[0].view(np.uint64):016x}','specific36':float(s[36]),'specific36_bits':f'{s[36].view(np.uint64):016x}'}
(O/'supplemental-release-numbers.json').write_text(json.dumps(r,indent=2))
