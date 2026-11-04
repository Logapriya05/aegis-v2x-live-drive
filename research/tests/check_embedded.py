"""The TwinTrust-AP core inside ../index.html must be byte-identical to port/twintrust_core.js (the tested port)."""
import pathlib, sys
here = pathlib.Path(__file__).resolve().parent.parent
port = (here / 'port' / 'twintrust_core.js').read_text()
core = port[:port.rindex('if (typeof module')].strip()
ok = core in (here.parent / 'index.html').read_text()
print('embedded core identical to tested port:', ok); sys.exit(0 if ok else 1)
