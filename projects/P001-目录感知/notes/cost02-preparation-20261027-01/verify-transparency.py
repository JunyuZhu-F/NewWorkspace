"""Restore only known diagnostic annotations, compare algorithm tokens to 004."""
import hashlib,json,re
from pathlib import Path
here=Path(__file__).resolve().parent;project=here.parent.parent
baseline=project/'experiments/EXP-20261027-004/source/code'
def undo(text):
    text=text.replace('#include "directory/diagnostics.hpp"\n','')
    text=re.sub(r'\bDIR_(?:CORE|PHASE)\(\w+\)','',text)
    for name in ['DIR_CATALOG_SCOPE','DIR_CATALOG_INIT','DIR_CATALOG_CONTROL']:text=text.replace(name,'')
    while 'DIR_VALUE(' in text:
        a=text.index('DIR_VALUE(');start=a+len('DIR_VALUE(');level=1;comma=None;i=start
        while level:
            c=text[i]
            if c=='(':level+=1
            elif c==')':level-=1
            elif c==',' and level==1 and comma is None:comma=i
            i+=1
        assert comma is not None
        text=text[:a]+text[comma+1:i-1].strip()+text[i:]
    return text
def tokens(text):
    text=re.sub(r'//[^\n]*|/\*.*?\*/','',text,flags=re.S)
    return re.findall(r'\w+|[^\s]',text)
checks={}
for name in ['src/index.cpp','src/path.cpp','include/directory/bitmap.hpp']:
    original=(baseline/name).read_text(encoding='utf-8');current=(project/'code'/name).read_text(encoding='utf-8')
    assert tokens(original)==tokens(undo(current)),name
    checks[name]='identical algorithm tokens after removing diagnostic-only annotations'
assert (baseline/'include/directory/index.hpp').read_bytes()==(project/'code/include/directory/index.hpp').read_bytes()
old=json.loads((project/'experiments/EXP-20261027-004/independent-verification.json').read_text())
for name,expected in old['binary_sha256'].items():
    assert hashlib.sha256((project/'code/build-Release'/name).read_bytes()).hexdigest()==expected
result={'status':'passed','scope':'annotation restoration/token check plus unchanged public layout header and preserved original Release binaries; not a formal proof of all diagnostics',
        'algorithm_token_checks':checks,'public_index_header_unchanged':True,'original_release_binaries_unchanged':True}
(here/'transparency.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
