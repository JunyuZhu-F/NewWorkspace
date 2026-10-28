# -*- coding: utf-8 -*-
"""Formal iteration adapter; core and frozen admission generator stay untouched."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

def render(source):
    spec=importlib.util.spec_from_file_location('scale_admission_generator',Path(__file__).resolve().parent.parent/'scale_directory/generate.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);data,changes=m.render(source);text=data.decode('utf-8')
    old='require(run==0 && warmups==0 && repeats==1 && std::string(argv[6])=="admission","admission only contract");'
    new='const std::string label=argv[6];require(run<5 && ((label=="formal" && warmups==3 && repeats==20) || (label=="entry-check" && warmups==0 && repeats==2)),"formal iteration contract");'
    assert text.count(old)==1;text=text.replace(old,new);changes.append(dict(old=old,new=new,count=1))
    old='Fixture fixture;std::ifstream input(f/"bindings.tsv");'
    new='require((label=="formal" && expected_rows==25000) || (label=="entry-check" && expected_rows==5000),"label shape contract");\n    '+old
    assert text.count(old)==1;text=text.replace(old,new);changes.append(dict(old=old,new=new,count=1))
    return text.encode('utf-8'),changes
if __name__=='__main__':
    source=Path(sys.argv[1]).read_bytes();dest=Path(sys.argv[2]);data,changes=render(source);dest.write_bytes(data)
    dest.with_suffix('.changes.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(source).hexdigest(),generated_sha256=hashlib.sha256(data).hexdigest(),changes=changes),indent=2)+'\n',encoding='utf-8')
