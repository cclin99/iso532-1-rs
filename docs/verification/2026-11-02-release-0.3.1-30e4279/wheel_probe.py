import iso532,numpy as np,importlib.metadata as m,json
r={'version':m.version('iso532'),'module':iso532.__file__,'numpy':np.__version__,'cases':[]}
assert r['version']=='0.3.1'
for name in ['loudness_zwst','loudness_zwtv']:
 x=np.zeros(4800);x[123]=np.nan
 try:getattr(iso532,name)(x,48000);raise AssertionError('did not reject')
 except ValueError as e:
  assert '123' in str(e);r['cases'].append({'function':name,'exception':'ValueError','message':str(e)})
print(json.dumps(r))
