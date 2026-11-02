import pathlib,subprocess,json,hashlib,re,sys,os,tomllib
out=pathlib.Path(__file__).resolve().parent;repo=out.parents[2];src=repo/'tmp/acceptance-031/source';tmp=repo/'tmp/acceptance-031';dist=repo/'tmp/dist-0.3.1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd,cwd=repo):
 p=subprocess.run(cmd,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);return {'exit_code':p.returncode,'output':p.stdout.decode('utf-8',errors='replace')}
py=tmp/'venv/Scripts/python.exe'
frozen={'commit':run(['git','rev-parse','30e4279'])['output'].strip(),'baseline_tag_object_sha':run(['git','rev-parse','v0.3.0'])['output'].strip(),'baseline_commit':run(['git','rev-parse','v0.3.0^{commit}'])['output'].strip(),'shared_head':run(['git','rev-parse','HEAD'])['output'].strip(),'status_porcelain':run(['git','status','--porcelain'])['output'],'source_archive_sha256':sha(tmp/'source.tar'),'baseline_archive_sha256':sha(tmp/'baseline.tar'),'toolchain':{n:run(c) for n,c in [('rustc',['rustc','-Vv']),('cargo',['cargo','-V']),('python',[str(py),'-V']),('packages',[str(py),'-c','import importlib.metadata as m; print({x:m.version(x) for x in ["numpy","maturin","pytest","mosqito","scipy"]})'])]}}
tracked=subprocess.check_output(['git','ls-tree','-r','--name-only','-z','30e4279'],cwd=repo).decode('utf-8').split('\0')
frozen['source_files']={n:sha(src/n) for n in tracked if n}
frozen['source_inventory_matches_git_tree']=all((src/n).is_file() for n in tracked if n)
frozen['input_files']={p.relative_to(src).as_posix():sha(p) for p in sorted((src/'data').rglob('*')) if p.is_file()}
(out/'freeze.json').write_text(json.dumps(frozen,indent=2),encoding='utf-8')
release=(src/'docs/RELEASE-0.3.1-2026-11-01.zh-TW.md').read_text(encoding='utf-8');sums=(dist/'SHA256SUMS.txt').read_text(encoding='utf-8-sig');art={}
for p in sorted(dist.iterdir()):
 h=sha(p);art[p.name]={'sha256':h,'bytes':p.stat().st_size,'matches_release':h in release if p.suffix!='.txt' else None,'matches_sums':h in sums if p.suffix!='.txt' else None}
art['header_matches_archive_copy']=(dist/'iso532.h').read_bytes()==(src/'iso532-ffi/include/iso532.h').read_bytes()
blob=subprocess.check_output(['git','show','30e4279:iso532-ffi/include/iso532.h'],cwd=repo)
art['header_matches_committed_blob']=(dist/'iso532.h').read_bytes()==blob
art['header_blob_sha256']=hashlib.sha256(blob).hexdigest()
art['header_archive_sha256']=sha(src/'iso532-ffi/include/iso532.h')
art['header_archive_eol_only_difference']=(src/'iso532-ffi/include/iso532.h').read_bytes().replace(b'\r\n',b'\n')==blob
art['git_core_autocrlf']=run(['git','config','--get','core.autocrlf'])['output'].strip()
(out/'artifacts.json').write_text(json.dumps(art,indent=2),encoding='utf-8')
versions={p:tomllib.loads((src/p).read_text())['package']['version'] for p in ['iso532/Cargo.toml','iso532-ffi/Cargo.toml','iso532-py/Cargo.toml']}
versions['Cargo.lock']={p['name']:p['version'] for p in tomllib.loads((src/'Cargo.lock').read_text())['package'] if p['name'] in ['iso532','iso532-ffi','iso532-py']}
citation=(src/'CITATION.cff').read_text();change=(src/'CHANGELOG.md').read_text();sec=change.split('0.3.1 - 2026-11-01')[1].split('\n## ')[0]
record={'versions':versions,'citation_version':bool(re.search(r'version:.*0\.3\.1',citation)),'citation_date':'2026-11-01' in citation,'changelog_claims':{x:x in sec for x in ['C-01','C-02','V-01']},'commits':run(['git','log','--reverse','--format=%H %s','v0.3.0..30e4279'])['output'].splitlines()}
record['commit_table_matches']=all(c.split()[0][:7] in release for c in record['commits'][:-1]) and record['commits'][-1].startswith(frozen['commit'])
record['ci']=json.loads((out/'ci.json').read_text(encoding='utf-8-sig'));record['ci_matches']=record['ci']['headSha']==frozen['commit'] and len(record['ci']['jobs'])==6 and all(j['conclusion']=='success' for j in record['ci']['jobs'])
(out/'records.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('freeze, artifacts and records written')
