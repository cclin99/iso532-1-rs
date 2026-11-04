"""Read-only OOXML audit of the Annex B.5 signal 15 reference and tolerance cells."""
import pathlib,sys,zipfile,xml.etree.ElementTree as E,json,hashlib,struct
import numpy as np
root=pathlib.Path(sys.argv[1]).resolve();out=pathlib.Path(__file__).resolve().parent
p=next((root/'tmp/c01-material/official/Annex B.5').glob('*.xlsx'))
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with zipfile.ZipFile(p) as z:
 strings=[''.join(x.itertext()) for x in E.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',ns)]
 workbook=E.fromstring(z.read('xl/workbook.xml'))
 sheets=[(x.attrib['name'],x.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']) for x in workbook.find('s:sheets',ns)]
 rel={x.attrib['Id']:x.attrib['Target'] for x in E.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
 name,rid=next(v for v in sheets if v[0]=='Test signal 15');path='xl/'+rel[rid]
 doc=E.fromstring(z.read(path));cells={}
 for c in doc.findall('.//s:c',ns):
  v=c.find('s:v',ns);f=c.find('s:f',ns);value=None if v is None else v.text
  if c.attrib.get('t')=='s' and value is not None:value=strings[int(value)]
  cells[c.attrib['r']]={'value':value,'formula':None if f is None else f.text}
 rows=[1,2,3,4,5,6,7,8,9,10,11,68,2245]
 selected={ref:v for ref,v in cells.items() if int(''.join(filter(str.isdigit,ref))) in rows}
 notes={ref:v for ref,v in cells.items() if isinstance(v['value'],str) and any(word in v['value'].lower() for word in ['calib','shift','delay','toler','level','silence','exception','test','copy'])}
r={'workbook_name':p.name,'workbook_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'sheet':name,'xml_member':path,'selected_cells':selected,'notes':notes,'comparison':'The release brief freezes max(0.1, 0.05*abs(ref)). Workbook columns C/D are 5% tolerance; G/H are separate 10% tolerance. N reference is B, time A. Row 2245 corresponds to output j=2234, t=4.468 s.'}
for ver in ['candidate','baseline']:
 n=np.fromfile(root/f'tmp/acceptance-040-astra/contracts-output-{ver}/sig15-n.bin',dtype='<f8');reference=float(cells['B2245']['value']);g=float(n[2234]);tol=max(.1,.05*abs(reference));r[ver]={'got':g,'got_bits':struct.pack('>d',g).hex(),'reference':reference,'reference_bits':struct.pack('>d',reference).hex(),'absolute_error':abs(g-reference),'tolerance':tol,'margin':tol-abs(g-reference),'workbook_5percent_min':cells['C2245'],'workbook_5percent_max':cells['D2245'],'workbook_10percent_min':cells['G2245'],'workbook_10percent_max':cells['H2245']}
(out/'sig15-workbook-audit.json').write_text(json.dumps(r,indent=2,ensure_ascii=False),encoding='utf8');print(json.dumps(r,indent=2,ensure_ascii=False))
