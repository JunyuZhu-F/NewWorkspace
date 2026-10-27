"""Archive small public primary-source documents; no dataset downloads."""
import datetime
import hashlib
import json
from pathlib import Path
import urllib.request

def main():
    out=Path(__file__).resolve().parent/'public-sources-01'
    out.mkdir(exist_ok=False)
    results=[]
    for name,url in [
        ('dataset-root.json','https://api.github.com/repos/KurtPatrickHere/dir-vector-dataset/contents/'),
        ('dataset-readme.md','https://raw.githubusercontent.com/KurtPatrickHere/dir-vector-dataset/main/README.md'),
        ('openviking-benchmark-readme.md','https://raw.githubusercontent.com/volcengine/OpenViking/main/benchmark/vectordb_perf/README.md')]:
        entry=dict(name=name,url=url,checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'WIKI-reproduction-readonly-audit'})
            with urllib.request.urlopen(req,timeout=25) as f:
                body=f.read(2*(1<<20)+1)
                if len(body)>2*(1<<20):raise ValueError('Small-source size limit exceeded')
                entry.update(status=f.status,etag=f.headers.get('ETag'))
            (out/name).write_bytes(body)
            entry.update(bytes=len(body),sha256=hashlib.sha256(body).hexdigest())
            if name=='dataset-root.json':entry['entries']=[x['name'] for x in json.loads(body)]
        except Exception as e:entry['error']=repr(e)
        results.append(entry)
    (out/'sources.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(results))

if __name__=='__main__':main()
