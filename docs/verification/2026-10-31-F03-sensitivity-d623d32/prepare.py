"""Prepare isolated sensitivity experiment; never writes tested sources or prior evidence."""
from pathlib import Path
import argparse, json, hashlib, shutil
p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--prior-work',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);a=p.parse_args()
d=a.destination.resolve();d.mkdir(parents=True,exist_ok=False);(d/'src').mkdir();(d/'c').mkdir()
here=Path(__file__).resolve().parent
table=(a.repo/'iso532/src/tables.rs').read_text(encoding='utf8')
slopes=(a.repo/'iso532/src/core/calc_slopes.rs').read_text(encoding='utf8')
old='[0.40, 0.33, 0.26, 0.24, 0.24, 0.22, 0.22, 0.22]'
new='[0.40, 0.33, 0.26, 0.24, 0.22, 0.22, 0.22, 0.22]'
assert table.count(old)==1
for name,text in [('tables.rs',table),('tables22.rs',table.replace(old,new)),('slopes24.rs',slopes),('slopes22.rs',slopes.replace('crate::tables::','crate::tables22::'))]:
 (d/'src'/name).write_text(text,encoding='utf8')
shutil.copyfile(here/'probe-main.rs.txt',d/'src/main.rs')
shutil.copyfile(here/'analyze.py',d/'analyze.py')
manifest='[package]\nname="f03-sensitivity-probe"\nversion="0.0.0"\nedition="2021"\n[workspace]\n[dependencies]\niso532={path='+json.dumps(str((a.repo/'iso532').resolve()))+'}\n'
(d/'Cargo.toml').write_text(manifest,encoding='utf8')
src=a.prior_work/'official/Annex A.4/ISO_532-1_LIB'
shutil.copyfile(src/'src/ISO_532-1.c',d/'c/ISO_532-1.c')
for h in (src/'include').glob('*.h'):shutil.copyfile(h,d/'c'/h.name)
print('Prepared',d)
