"""Source-linked descriptive quality/latency figures; no paper-number equivalence."""
import argparse
import csv
import json
import pathlib
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--experiment',type=pathlib.Path,required=True);ap.add_argument('--skill-scripts',type=pathlib.Path,required=True);a=ap.parse_args()
    sys.path.insert(0,str(a.skill_scripts))
    from audit_panel_alignment import require_matplotlib_panel_alignment
    report=json.loads((a.experiment/'verification.json').read_text(encoding='utf-8'))
    assert report['status']=='passed' and report['formal'] and report['raw_timing_rows']==1202400
    out=a.experiment/'figures';out.mkdir(exist_ok=False)
    # Contract: comparison of three scope resolvers at matched search quality.
    # Separate single-axis figures show distinct recursive/non-recursive semantics.
    # No superiority claim is assumed. All 501/235 nonempty requests are retained.
    contract=dict(question='How do scope resolvers trade total latency at the same search quality under a shared fixed backend?',claim='Quality equality and observed latency differences are descriptive for this independent 10k time sample; no original Viking or universal speedup claim.',archetype='quantitative grid, two separate single-axis figures',backend='Python/matplotlib',export='127 x 105 mm; SVG/PDF editable text and 600dpi PNG/TIFF; glyphs >= 5pt; no submission journal specified',n='5 independent processes, same deterministic ANN seed/data; 20 timed sweeps after 3 warmups; repeated calls are technical repeats',uncertainty='horizontal SD (ddof=1) of five per-process nonempty mean latencies, not a confidence interval',test='none, descriptive; no multiple-comparison p-values',exclusions='266 empty nonrecursive year scopes omitted only from Recall and primary curves; all-request and empty latencies retained in results table',integrity='No observations trimmed. No image manipulation, interpolation, smoothing, or log transform.',alignment='single axis per exported figure; run helper to record not applicable',sources=['verification.json','figures/curves.csv','figures/paired-differences.csv'])
    (out/'contract.json').write_text(json.dumps(contract,indent=2)+'\n',encoding='utf-8')
    quality={(r['recursive'],r['probes']):r for r in report['quality']}
    groups={(r['strategy'],r['recursive'],r['probes'],r['empty']):r for r in report['groups']}
    workers=report['workers']
    styles={'PE-ONLINE':('#4477AA','o'),'PE-OFFLINE':('#888888','s'),'TrieHI':('#228833','^')}
    data=[]
    for recursive in (True,False):
        for probes in (0,1,4,16):
            q=quality[(recursive,probes)]
            for strategy in styles:
                means=[]
                for worker in workers:
                    g=next(r for r in worker['groups'] if (r['strategy'],r['recursive'],r['probes'],r['empty'])==(strategy,recursive,probes,False))
                    means.append(g['total']['mean_ns']/1000)
                g=groups[(strategy,recursive,probes,False)]
                assert np.isclose(np.mean(means),g['total']['mean_ns']/1000,rtol=1e-12)
                data.append(dict(recursive=recursive,strategy=strategy,probes=probes,nonempty=q['nonempty'],empty=q['empty'],recall=q['mean_recall_nonempty'],mean_us=float(np.mean(means)),sd_process_mean_us=float(np.std(means,ddof=1)),**{f'run{i}_mean_us':v for i,v in enumerate(means)}))
    with (out/'curves.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
    lookup={(r['strategy'],r['recursive'],r['probes']):r for r in data}
    paired=[]
    for recursive in (False,True):
        for probes in (0,1,4,16):
            base=lookup[('PE-ONLINE',recursive,probes)]
            for strategy in ('PE-OFFLINE','TrieHI'):
                row=lookup[(strategy,recursive,probes)]
                for run in range(5):
                    delta=row[f'run{run}_mean_us']-base[f'run{run}_mean_us']
                    paired.append(dict(recursive=recursive,probes=probes,strategy=strategy,baseline='PE-ONLINE',run=run,paired_process_mean_delta_us=delta))
    with (out/'paired-differences.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(paired[0]));writer.writeheader();writer.writerows(paired)
    plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans'],'font.size':8,'axes.labelsize':8,'xtick.labelsize':7,'ytick.labelsize':7,'legend.fontsize':7,'pdf.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.7,'savefig.dpi':300})
    for recursive in (True,False):
        name='recursive' if recursive else 'nonrecursive'
        width_mm=127
        fig=plt.figure(figsize=(width_mm/25.4,105/25.4),facecolor='white')
        ax=fig.add_axes([.18,.32,.76,.53])
        for strategy,(color,marker) in styles.items():
            rows=[lookup[(strategy,recursive,p)] for p in (1,4,16)]
            ax.errorbar([r['mean_us'] for r in rows],[r['recall'] for r in rows],xerr=[r['sd_process_mean_us'] for r in rows],color=color,marker=marker,markersize=4,linewidth=.9,elinewidth=.7,capsize=2,label=strategy)
            exact=lookup[(strategy,recursive,0)]
            ax.errorbar(exact['mean_us'],exact['recall'],xerr=exact['sd_process_mean_us'],marker='x',color=color,markersize=5,linestyle='none',elinewidth=.7,capsize=2)
        ax.set_xlabel('Mean total latency (microseconds)')
        ax.set_ylabel('Macro Recall@100 (nonempty scopes)')
        ax.set_ylim(-.04,1.08);ax.set_xlim(left=0);ax.set_yticks([0,.25,.5,.75,1])
        ax.grid(axis='y',color='#DDDDDD',linewidth=.4)
        fig.text(.5,.96,('Recursive' if recursive else 'Nonrecursive')+' time queries',ha='center',fontsize=10)
        q=quality[(recursive,0)]
        fig.text(.5,.89,f"Independent backend; 10,000 vectors; {q['nonempty']} nonempty requests",ha='center',fontsize=7)
        handles=[Line2D([0],[0],color=color,marker=marker,linewidth=.9,markersize=4,label=strategy) for strategy,(color,marker) in styles.items()]
        fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.13),ncol=3,frameon=False,columnspacing=1.5)
        fig.text(.5,.065,'Connected IVF points: nprobe 1, 4, 16; x: exact search',ha='center',fontsize=7)
        fig.text(.5,.025,'Horizontal bars: SD of five process means (not a confidence interval)',ha='center',fontsize=7)
        fig.canvas.draw()
        require_matplotlib_panel_alignment(fig,json_out=str(out/(name+'.alignment.json')),overlay_svg=str(out/(name+'.alignment.svg')),tolerance_pt=1.5,gutter_tolerance_pt=1.5,strict=True)
        fig.savefig(out/(name+'.svg'))
        fig.savefig(out/(name+'.pdf'))
        fig.savefig(out/(name+'.png'),dpi=600)
        fig.savefig(out/(name+'.tiff'),dpi=600,pil_kwargs={'compression':'tiff_lzw'})
        plt.close(fig)
    lines=['# SEARCH-02 measured results','', 'Independent exact/IVF prototype; deterministic cross-time 10k sample; not Viking or author-number reproduction. All reported results passed independent verification.','', '| Mode | Backend | Nonempty / empty | Recall@100 nonempty | ONLINE total us | OFFLINE total us | TrieHI total us |','|---|---|---|---:|---:|---:|---:|']
    for recursive in (True,False):
        for probes in (0,1,4,16):
            q=quality[(recursive,probes)]
            means=[lookup[(s,recursive,probes)]['mean_us'] for s in styles]
            lines.append(f"| {'recursive' if recursive else 'nonrecursive'} | {'exact' if probes==0 else 'IVF '+str(probes)} | {q['nonempty']} / {q['empty']} | {q['mean_recall_nonempty']:.6f} | "+' | '.join(f'{v:.4f}' for v in means)+' |')
    lines+=['','These are nonempty-query means. Empty year-local requests are not counted as Recall=1. Exact and nprobe16 agree with independently recomputed subset truth. Partial-probe quality is identical across directory strategies; lower recall is retained.','', '## All-request and empty latencies','', '| Mode | Backend | Strategy | All-request mean us | Empty-request mean us |','|---|---|---|---:|---:|']
    for recursive in (True,False):
        for probes in (0,1,4,16):
            for strategy in styles:
                available=[groups[k]['total'] for k in groups if k[:3]==(strategy,recursive,probes)]
                mean=sum(x['mean_ns']*x['count'] for x in available)/sum(x['count'] for x in available)/1000
                empty=groups.get((strategy,recursive,probes,True))
                empty_text=f"{empty['total']['mean_ns']/1000:.4f}" if empty else 'n/a'
                lines.append(f"| {'recursive' if recursive else 'nonrecursive'} | {probes} | {strategy} | {mean:.4f} | {empty_text} |")
    lines+=['','## Measurement limits','', 'Five independent processes, same ANN training seed and data; 3 warmups and 20 measured sweeps. Curves retain every nonempty request. Error bars are descriptive SD of process means. Per-query timings, nearest-rank percentiles, per-run summaries, and sampled stop-limit telemetry remain in the raw evidence. No significance, generalization, or stable extreme-tail claim is made.','', 'The backend scans allowed IDs and checks partitions rather than optimized posting traversal. Stage-clock reads, ID mapping, outside-timer correctness checks and warm-cache execution affect these results. Total latency excludes load/train/build, output serialization, transport, and final caller-owned temporary destruction; the protocol defines the exact boundaries.','', 'All timings and recalls are kept, including counterexamples. The cross-time input has 423 directories and is not directly comparable to the earlier 34-directory prefix sample. Missing source year 1995 is not investigated or filled. PG/WIKI, author distance/Viking configuration and full-scale experiments remain outside this completed small branch.','']
    (a.experiment/'results.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(dict(status='rendered',figure_count=2,source_rows=len(data),paired_rows=len(paired))))


if __name__=='__main__':main()
