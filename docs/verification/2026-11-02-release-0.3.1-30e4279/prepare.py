"""Prepare isolated archives and verification environments; run from repository root.
Dependencies may require network access. No source, tests, goldens, tags or branches change.
"""
import pathlib,subprocess,tarfile,shutil,sys,json
repo=pathlib.Path(__file__).resolve().parents[3];tmp=repo/'tmp/acceptance-031';tmp.mkdir(exist_ok=True)
def run(*cmd):subprocess.run([str(x) for x in cmd],cwd=repo,check=True)
extraction={}
for name,revision in [('source','30e427963da88db8b23e82cf612f047f36cd164b'),('baseline','62e46ca7d6ac65df7c4a4db8df8380e30234e267')]:
 archive=tmp/(name+'.tar');folder=tmp/name;folder.mkdir(exist_ok=True)
 run('git','archive','--format=tar','--output='+str(archive),revision)
 with tarfile.open(archive) as t:
  names=[m.name for m in t.getmembers() if m.isfile()];t.extractall(folder,filter='data')
 extraction[name]={'method':'Python tarfile','missing_after':[n for n in names if not (folder/n).is_file()]}
 assert not extraction[name]['missing_after']
 shutil.copytree(repo/'data',folder/'data',dirs_exist_ok=True)
# Full build/test environment. The observed run used an equivalent isolated venv
# with dependency .pth to the existing golden environment and a copied maturin.exe.
run(sys.executable,'-m','venv',tmp/'venv')
py=tmp/'venv/Scripts/python.exe'
run(py,'-m','pip','install','numpy==2.4.6','scipy==1.17.1','maturin==1.14.1','pytest==9.1.1','mosqito==1.2.1')
run(sys.executable,'-m','venv',tmp/'wheel-venv')
run(tmp/'wheel-venv/Scripts/python.exe','-m','pip','install','numpy==2.4.6',repo/'tmp/dist-0.3.1/iso532-0.3.1-cp39-abi3-win_amd64.whl')

(pathlib.Path(__file__).resolve().parent/'archive-extraction.json').write_text(json.dumps(extraction,indent=2),encoding='utf-8')
