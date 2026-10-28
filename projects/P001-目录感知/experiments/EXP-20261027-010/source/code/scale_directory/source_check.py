# -*- coding: utf-8 -*-
"""Independent selected-record reread of pinned, pretty-printed metadata (no vectors)."""
import hashlib
import json
from pathlib import Path
import sys
import time

def main():
    started=time.perf_counter();root=Path(sys.argv[1]);result={}
    for ds in ['arxiv','wiki']:
        fixtures=[root/f'{ds}-{n}' for n in [5000,25000]]
        manifests=[json.loads((f/'manifest.json').read_text(encoding='utf-8')) for f in fixtures]
        wanted={}
        for f in fixtures:
            for r in json.loads((f/'sample.json').read_text(encoding='utf-8')):
                i=r['global_id'];assert i not in wanted or wanted[i]==r['path'];wanted[i]=r['path']
        source=Path(manifests[0]['source']);before=source.stat();h=hashlib.sha256();found=0;count=0
        with source.open('rb') as stream:
            if ds=='arxiv':
                for i,line in enumerate(stream):
                    h.update(line)
                    if i in wanted:
                        gid,p=line.decode('utf-8').rstrip('\r\n').split('\t');assert int(gid)==i and p==wanted[i];found+=1
                    count+=1
            else:
                # This parser intentionally differs from preparation's streaming JSON decoder.
                # The full-file pinned SHA checks the layout and content, not arbitrary JSON input.
                block=None
                for line in stream:
                    h.update(line);s=line.strip()
                    if s==b'{':assert block is None;block=[line]
                    elif block is not None:
                        if s in [b'}',b'},']:
                            block.append(b'}');obj=json.loads(b''.join(block));assert obj['id']==count
                            if count in wanted:assert obj['path']==wanted[count];found+=1
                            count+=1;block=None
                        else:block.append(line)
                assert block is None
        after=source.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
        assert found==len(wanted) and count==manifests[0]['source_records']
        assert all(h.hexdigest()==m['source_proof']['sha256'] and before.st_size==m['source_proof']['size'] and before.st_mtime_ns==m['source_proof']['mtime_ns'] for m in manifests)
        result[ds]=dict(sha256=h.hexdigest(),records=count,selected_verified=found,size=before.st_size,mtime_ns=before.st_mtime_ns)
        print('PASS independent source',ds,count,flush=True)
    result.update(status='passed',elapsed_s=time.perf_counter()-started,vector_payload_bytes_read=0)
    dest=Path(sys.argv[2]);assert not dest.exists();dest.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
