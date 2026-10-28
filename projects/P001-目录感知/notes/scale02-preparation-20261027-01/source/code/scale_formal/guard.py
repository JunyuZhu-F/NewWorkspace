# -*- coding: utf-8 -*-
"""Serial command guard, with an encompassing dataset deadline."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import psutil

P=Path.cwd();G=1<<30
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

class Guard:
    def __init__(self,root,unit_seconds=None):
        self.root=root;root.mkdir(parents=True,exist_ok=True);assert not (root/'commands.json').exists()
        self.commands=[];self.start=time.perf_counter();self.deadline=None if unit_seconds is None else self.start+unit_seconds
        self.status=dict(status='running',started_utc=now(),unit_seconds=unit_seconds,completed_commands=0)
        save(root/'status.json',self.status)
    def remaining(self):
        return float('inf') if self.deadline is None else self.deadline-time.perf_counter()
    def gate(self,name,stable):
        samples=[];start=time.perf_counter()
        try:
            while True:
                a=psutil.virtual_memory().available;disk=shutil.disk_usage(P).free
                samples.append(dict(utc=now(),elapsed_s=time.perf_counter()-start,available_bytes=a,disk_free_bytes=disk,unit_remaining_s=None if self.deadline is None else self.remaining()))
                if self.remaining()<=0:raise RuntimeError('resource unit deadline in preflight')
                if a<4*G or disk<10*G:raise RuntimeError('resource preflight requires available >=4GiB and disk >=10GiB')
                if not stable or time.perf_counter()-start>=20:break
                time.sleep(min(1,self.remaining()))
        finally:save(self.root/f'{name}-preflight.json',dict(stable_required_s=20 if stable else 0,samples=samples))
    def run(self,name,cmd,stable=True,env=None,expected=0,marker=None):
        self.gate(name,stable);assert self.remaining()>0
        row=dict(name=name,command=[str(x) for x in cmd],started_utc=now(),expected_exit=expected)
        self.commands.append(row);save(self.root/'commands.json',self.commands)
        log=self.root/f'{name}.log';assert not log.exists();start=time.perf_counter();samples=[];proc=None;violation=None
        try:
            with log.open('wb') as stream:
                proc=subprocess.Popen(row['command'],cwd=P,stdout=stream,stderr=subprocess.STDOUT,env=env);row['pid']=proc.pid;rootproc=psutil.Process(proc.pid)
                while True:
                    next_tick=time.perf_counter()+.10;elapsed=time.perf_counter()-start;tree=[];private=0
                    try:tree=[rootproc]+rootproc.children(recursive=True)
                    except psutil.NoSuchProcess:pass
                    for child in tree:
                        try:private+=child.memory_info().private
                        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
                    available=psutil.virtual_memory().available
                    samples.append(dict(elapsed_s=elapsed,private_tree_bytes=private,available_bytes=available))
                    output_bytes=sum(f.stat().st_size for f in self.root.rglob('*') if f.is_file())
                    if private>2*G or available<2*G or elapsed>600 or self.remaining()<=0 or output_bytes>G:
                        violation=dict(private=private,available=available,elapsed_s=elapsed,remaining_s=None if self.deadline is None else self.remaining(),output_bytes=output_bytes)
                        for child in reversed(tree):
                            try:child.kill()
                            except psutil.NoSuchProcess:pass
                        if proc.poll() is None:proc.kill()
                        proc.wait();raise RuntimeError('resource runtime stop '+str(violation))
                    if proc.poll() is not None:break
                    time.sleep(max(0,next_tick-time.perf_counter()))
                row['exit_code']=proc.returncode;assert proc.returncode==expected,('unexpected exit',name,proc.returncode)
            if marker:assert marker in log.read_text(encoding='utf-8',errors='replace'),'expected error marker absent'
        finally:
            if proc is not None and proc.poll() is None:proc.kill();proc.wait()
            gap=max([b['elapsed_s']-a['elapsed_s'] for a,b in zip(samples,samples[1:])] or [0])
            row.update(finished_utc=now(),elapsed_s=time.perf_counter()-start,unit_elapsed_s=time.perf_counter()-self.start,private_peak_sampled_bytes=max([s['private_tree_bytes'] for s in samples] or [0]),available_min_sampled_bytes=min([s['available_bytes'] for s in samples] or [psutil.virtual_memory().available]),maximum_sample_gap_s=gap,violation=violation)
            save(self.root/f'{name}-monitor.json',dict(**row,target_period_s=.10,samples=samples));save(self.root/'commands.json',self.commands)
        assert gap<=.25,'resource sampling gap >250ms; output retained, admission not accepted'
        self.status['completed_commands']+=1;save(self.root/'status.json',self.status)
        print('PASS',self.root.name,name,round(row['elapsed_s'],3),'s',flush=True);return row
    def finish(self,status,**kw):
        self.status.update(status=status,finished_utc=now(),elapsed_s=time.perf_counter()-self.start,**kw);save(self.root/'status.json',self.status)
