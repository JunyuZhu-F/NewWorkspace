# -*- coding: utf-8 -*-
"""Targeted monitor repair check; reuse validated artifacts, no benchmark worker."""
import json
from pathlib import Path
import sys
import pipeline

def main():
    original=Path(sys.argv[1]);r=pipeline.Runner(original/'monitor-recheck-01')
    try:
        initial={}
        for p in original.glob('*-monitor.json'):
            samples=pipeline.load(p)['samples'];gap=max([b['elapsed_s']-a['elapsed_s'] for a,b in zip(samples,samples[1:])] or [0])
            initial[p.name]=gap
        pipeline.save(r.root/'initial-sampling-audit.json',dict(maximum_gap_s=max(initial.values()),per_command=initial,initial_gap_within_250ms=all(x<=.25 for x in initial.values()),assessment='Original correctness and budget samples valid; strict <=250ms original monitoring criterion NOT met. Preserve all initial files unchanged.'))
        hashes={str(p.relative_to(pipeline.P)):pipeline.sha(p) for p in pipeline.CODE.glob('*.py')}
        pipeline.save(r.root/'source-hashes.json',hashes)
        for ds in ['arxiv','wiki']:
            r.run('recheck-'+ds,[sys.executable,'-B',pipeline.CODE/'verify.py',original/'fixtures'/f'{ds}-25000',r.root/f'verification-{ds}.json',original/'outputs'/f'{ds}-25000-release'])
        monitors=[pipeline.load(p) for p in r.root.glob('*-monitor.json')]
        assert len(monitors)==2 and all(m['observed_gap_within_250ms'] for m in monitors),'corrected sampler actual spacing exceeded 250ms'
        assert pipeline.frozen()==pipeline.load(original/'old-46-source-hashes.json')
        r.status.update(status='passed',finished_utc=pipeline.now(),benchmark_workers_repeated=0,initial_monitoring_deviation_retained=True,maximum_corrected_gap_s=max(m['maximum_observed_sample_gap_s'] for m in monitors))
        pipeline.save(r.root/'final-check.json',r.status)
    except Exception as e:
        r.status.update(status='failed',error=repr(e),finished_utc=pipeline.now());raise
    finally:pipeline.save(r.root/'status.json',r.status)
if __name__=='__main__':main()
