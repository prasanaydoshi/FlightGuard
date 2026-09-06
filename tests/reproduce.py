"""Compare regenerated artifacts with a small cross-platform floating-point tolerance."""
import json
import math
import pathlib
import sys

def equal(a,b,path='root'):
    if isinstance(a,dict):
        assert a.keys()==b.keys(),path
        for k in a:equal(a[k],b[k],path+'.'+k)
    elif isinstance(a,list):
        assert len(a)==len(b),path
        for i,(x,y) in enumerate(zip(a,b)):equal(x,y,path+f'[{i}]')
    elif isinstance(a,float):
        assert math.isclose(a,b,rel_tol=1e-8,abs_tol=1e-10),(path,a,b)
    else:assert a==b,(path,a,b)

if __name__=='__main__':
    for name in ['model.json','evaluation.json','replay.json']:
        equal(json.loads(pathlib.Path('web',name).read_text()),json.loads(pathlib.Path(sys.argv[1],name).read_text()))
    print('Model, evaluation and replay reproduced within cross-platform numerical tolerance')
