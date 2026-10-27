# -*- coding: utf-8 -*-
"""Export already independently verified statistics; no timing reruns."""
import csv
import hashlib
import json
from pathlib import Path
import statistics
import math
from collections import defaultdict

P=Path.cwd()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def csv_out(p,rows):
    with p.open('x',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')

def main():
    for exp,kind in [('EXP-20261027-007','directory'),('EXP-20261027-008','search')]:
        root=P/'experiments'/exp
        assert load(root/'status.json')['status']=='passed'
        analysis=root/'analysis-01';analysis.mkdir(exist_ok=False)
        if kind=='directory':
            data=load(root/'verification-directory-default.json');phase=load(root/'verification-directory-phase.json')
            rows=[]
            for mode,report in [('default',data),('phase',phase)]:
                assert report['status']=='passed'
                for g in report['groups']:
                    r=dict(mode=mode,strategy=g['strategy'],kind=g['kind'],case=g['case'],count=g['total']['count'])
                    for component in ('total','directory_misc','locate','bitmap_copy','bitmap_sets','ancestors','catalog','cleanup'):
                        for name,v in g[component].items():
                            if name!='count':r[component+'_'+name]=v
                    rows.append(r)
            csv_out(analysis/'statistics.csv',rows)
            csv_out(analysis/'operations.csv',data['operations'])
            prep=P/load(root/'config.json')['preparation'];geometry={x['case']:x for x in load(prep/'fixture/directory-cases.json')}
            bydepth=defaultdict(list);bycase=defaultdict(list)
            for worker in data['workers']:
                with (P/worker['output']/'timings.tsv').open(encoding='utf-8',newline='') as h:
                    for r in csv.DictReader(h,delimiter='\t'):
                        if r['kind']!='query' or r['warmup']!='0':continue
                        g=geometry[r['case']];value=int(r['total_ns']);bydepth[(r['strategy'],g['depth'],g['recursive'],g['candidates']==0)].append(value);bycase[(r['strategy'],r['case'])].append(value)
            def describe(v):
                a=sorted(v)
                return dict(count=len(a),mean_ns=sum(a)/len(a),**{f'p{q}_ns':a[math.ceil(float(q)/100*len(a))-1] for q in ('90','95','99','99.9')})
            csv_out(analysis/'query-by-depth.csv',[dict(strategy=k[0],depth=k[1],recursive=k[2],empty=k[3],**describe(v)) for k,v in sorted(bydepth.items())])
            csv_out(analysis/'query-by-case.csv',[dict(strategy=k[0],**geometry[k[1]],**describe(v)) for k,v in sorted(bycase.items())])
            for g in data['groups']:
                if g['kind']!='query':continue
                v=[x for (s,c),values in bycase.items() if s==g['strategy'] and str(geometry[c]['recursive'])==g['case'] for x in values]
                assert len(v)==g['total']['count'] and abs(sum(v)/len(v)-g['total']['mean_ns'])<1e-8
            portable=data['workers'][0]['portable'];csv_out(analysis/'portable.csv',portable)
            table=['# WIKI独立小规模目录性能结果','','真实WIKI 10000条样本，项目生成查询/连续维护，不是作者原始工作负载。默认/phase各5独立进程×20测量pass，预热排除。下表为默认API平均值，未扣catalog或探针开销。','','| 操作 | PE-ONLINE μs | PE-OFFLINE μs | TrieHI μs |','|---|---:|---:|---:|']
            for k,c,label in [('build','build','构建'),('query','True','递归DSQ'),('query','False','非递归DSQ'),('move','move-large','MOVE大子树'),('merge','merge-large','MERGE大子树'),('move','move-deep','MOVE深末端'),('merge','merge-deep','MERGE深末端')]:
                values=[next(g['total']['mean_ns']/1000 for g in data['groups'] if g['strategy']==s and g['kind']==k and g['case']==c) for s in ('PE-ONLINE','PE-OFFLINE','TrieHI')]
                table.append('| '+label+' | '+' | '.join(f'{v:.4f}' for v in values)+' |')
            table+=['','全部均值/nearest-rank P90/P95/P99/P99.9及各阶段在analysis-01/statistics.csv，逐进程统计在verification文件，原始重复值在run-*/timings.tsv。查询按58case等权，包含空范围；目录深度/候选量/fanout见冻结fixture的directory-cases.json，4项维护规模见operations.csv。','','phase直接catalog值只解释相应诊断构建，不从默认时间中相减；未观测区间不补造。portable.csv仅Roaring portable字节，不是完整索引大小、物理堆或进程独占；catalog为10000条的公共映射，时间由phase直接记录。每个pass重新构建索引，查询及连续维护共享该pass缓存状态，正确性判定在计时外仍可能影响缓存。','','有限小样本和固定4操作不能证明一般加速；全部反例保留。未控制背景负载，不做显著性或尾部稳定性声明。独立统计/全部计时格位/全部候选状态由verification-directory-*.json验证。']
        else:
            data=load(root/'verification-search-search.json');assert data['status']=='passed'
            rows=[]
            for g in data['groups']:
                r={k:g[k] for k in ('strategy','recursive','probes','empty')}
                for component in ('directory','materialize','ranking','total'):
                    for name,v in g[component].items():r[component+'_'+name]=v
                means=[next(x['total']['mean_ns'] for x in w['groups'] if all(x[k]==g[k] for k in ('strategy','recursive','probes','empty'))) for w in data['workers']]
                r['run_mean_sample_sd_ns']=statistics.stdev(means);rows.append(r)
            csv_out(analysis/'statistics.csv',rows);csv_out(analysis/'quality.csv',data['quality'])
            paired=[]
            for w in data['workers']:
                for r in (False,True):
                    for probe in (0,1,4,16):
                        means={s:next(x['total']['mean_ns'] for x in w['groups'] if x['strategy']==s and x['recursive']==r and x['probes']==probe and not x['empty']) for s in ('PE-ONLINE','PE-OFFLINE','TrieHI')}
                        paired.append(dict(run=w['run'],recursive=r,probes=probe,offline_minus_online_ns=means['PE-OFFLINE']-means['PE-ONLINE'],triehi_minus_online_ns=means['TrieHI']-means['PE-ONLINE']))
            csv_out(analysis/'paired-differences.csv',paired)
            table=['# WIKI独立L2/IVF小规模检索结果','','真实WIKI 10000样本＋456原query向量；目录由ID/固定哈希配对，与文本意图未作相关性对齐。k10，平方L2、不归一化、16中心/种子42/8次Lloyd，exact及nprobe1/4/16；不是Viking或原文工作负载。nDCG本轮不报告，qrels未用于选样/配目录/调参。','','| 模式 | probe | 非空/空case | Recall@10 | ONLINE总均值 μs | OFFLINE总均值 μs | TrieHI总均值 μs |','|---|---:|---:|---:|---:|---:|---:|']
            for r in (True,False):
                for probe in (0,1,4,16):
                    quality=next(x for x in data['quality'] if x['recursive']==r and x['probes']==probe)
                    values=[next(g['total']['mean_ns']/1000 for g in data['groups'] if g['strategy']==s and g['recursive']==r and g['probes']==probe and not g['empty']) for s in ('PE-ONLINE','PE-OFFLINE','TrieHI')]
                    table.append('| '+('递归' if r else '非递归')+' | '+('exact' if probe==0 else str(probe))+f" | {quality['nonempty']}/{quality['empty']} | {quality['mean_recall_nonempty']:.6f} | "+' | '.join(f'{v:.4f}' for v in values)+' |')
            table+=['','主表只汇总非空case，空范围质量null、延迟仍单列在statistics.csv及原始文件，未剔除。Recall分母min(10,目录候选量)，所有策略同候选与后端/结果；exact及全探测非空Recall=1由独立GT核验。','','总延迟直接分目录、global/dense转换、后端排名三个区间；排除加载/聚类构建/目录建树/序列化与最后临时集合释放，不是完整服务请求延迟。目录以外阶段也有缓存与执行波动，不能将全部总差异归因目录算法。低召回和反例全部保留，不做显著性或尾部稳定性声明。','','statistics.csv含全部阶段/分位数/空范围/5进程均值样本SD，SD不是置信区间；paired-differences.csv保存每进程配对差。底层仍遍历允许ID并过滤分区，不是优化倒排IVF实现；quality.csv报告的是本项目目录范围内精确近邻召回，不能解读为自然查询相关性质量。']
        (root/'results.md').write_text('\n'.join(table)+'\n',encoding='utf-8')
        save(analysis/'provenance.json',dict(source_reports={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob('verification-*.json')},export_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),exports={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in analysis.iterdir() if p.is_file()}))
        print(exp,'exported')
if __name__=='__main__':main()
