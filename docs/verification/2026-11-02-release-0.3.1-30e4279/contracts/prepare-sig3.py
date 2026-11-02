import pathlib,json,hashlib
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly
root=pathlib.Path('tmp/acceptance-031/source')
p=root/'data/annexb/Test signal 3 (1 kHz 60 dB)_44100Hz.wav'
fs,x=wavfile.read(p);assert fs==44100 and x.dtype==np.int16
pressure=x.astype(np.float64)*(2*np.sqrt(2)/32768)
y=np.ascontiguousarray(resample_poly(pressure,160,147),dtype='<f8')
target=pathlib.Path('tmp/acceptance-031/sig3-pressure.bin');target.write_bytes(y.tobytes())
meta=dict(source=str(p),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),source_rate=fs,source_samples=len(x),source_dtype=str(x.dtype),pressure_scale='2*sqrt(2)/32768',resampler='scipy.signal.resample_poly(pressure,160,147), default window/zero padding',scipy=__import__('scipy').__version__,numpy=np.__version__,output=str(target),output_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),output_samples=len(y))
pathlib.Path(__file__).resolve().parent.joinpath('sig3-input.json').write_text(json.dumps(meta,indent=2),encoding='utf8')
