# -*- coding: utf-8 -*-
"""Read-only audit of measured data; write factual records and evidence manifests."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import psutil

P=Path.cwd();ROOT=P/'notes/scale02-preparation-20261027-03';G=1<<30
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def sourcecheck(root):
    hashes=load(root/'source-hashes.json')
    assert all(sha(P/k)==v and sha(root/'source'/k)==v for k,v in hashes.items())
    return len(hashes)
def monitorcheck(root,count):
    commands=load(root/'commands.json');assert len(commands)==count
    for c in commands:
        m=load(root/(c['name']+'-monitor.json'));assert c=={k:m[k] for k in c}
        assert c['exit_code']==c['expected_exit'] and c['violation'] is None
        assert c['maximum_sample_gap_s']<=.25 and c['private_peak_sampled_bytes']<=2*G and c['available_min_sampled_bytes']>=2*G and c['elapsed_s']<=600
        gate=load(root/(c['name']+'-preflight.json'));s=gate['samples'];assert s[-1]['elapsed_s']-s[0]['elapsed_s']>=gate['stable_required_s']-.001
        assert all(x['available_bytes']>=4*G and x['disk_free_bytes']>=10*G for x in s)
    return commands
def main():
    overall=load(ROOT/'overall-status.json');assert overall['status']=='passed'
    assert load(ROOT/'entry-final-check.json')['status']=='passed'
    assert load(ROOT/'deadline-contract/status.json')['status']=='passed_expected_stop'
    old=load(ROOT/'old-53-source-hashes.json');assert len(old)==53 and all(sha(P/k)==v for k,v in old.items())
    sourcecheck(ROOT);prepcommands=load(ROOT/'commands.json');monitorcheck(ROOT,len(prepcommands))
    original=P/'notes/scale02-preparation-20261027-01'
    monitorcheck(original,len(load(original/'commands.json')))
    previous_sources=load(original/'source-hashes.json')
    assert all(sha(original/'source'/k)==v for k,v in previous_sources.items())
    assert all(sha(P/k)==v for k,v in previous_sources.items() if (P/k).resolve()!=(P/'code/scale_formal/pipeline.py').resolve())
    assert load(ROOT/'reuse-provenance.json')['native_workers_repeated']==0
    # Generated source reconstruction is separate from the build's stored hash assertion.
    import importlib.util
    spec=importlib.util.spec_from_file_location('formal_source_review',P/'code/scale_formal/generate.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    generated,changes=m.render((P/'code/wiki_experiment/directory.cpp').read_bytes());assert len(changes)==13
    for build in ['release','asan']:
        b=ROOT/'builds'/build;assert (b/'scale_formal.cpp').read_bytes()==generated
        assert sha(b/'scale_formal.exe')==load(b/'binary.json')['sha256']
        assert ('/fsanitize=address' in (b/'build.ninja').read_text(encoding='utf-8'))==(build=='asan')
    summaries=[]
    for ds,exp,want in [('wiki','EXP-20261027-009',(23115,20100,3015,106950)),('arxiv','EXP-20261027-010',(8625,7500,1125,34500))]:
        r=P/'experiments'/exp;status=load(r/'status.json');assert status['status']=='passed' and status['elapsed_s']<=1800
        commands=monitorcheck(r,6);source_entries=sourcecheck(r);v=load(r/'analysis-01/verification.json');assert v['status']=='passed'
        assert (v['timing_rows'],v['measurement_rows'],v['warmup_rows'],v['full_scope_checks'])==want
        assert len(v['runs'])==5 and [s['run'] for s in v['runs']]==list(range(5))
        config=load(r/'config.json');f=Path(config['fixture']);manifest=load(f/'manifest.json')
        original=P/'notes/scale-prep-20261027-02/fixtures'/f'{ds}-25000'
        assert all(sha(f/x)==h and sha(original/x)==h for x,h in manifest['files'].items())
        assert sha(f/'manifest.json')==sha(original/'manifest.json')
        assert sha(r/'protocol.md')==sha(P/'notes/scale02-protocol-20261027.md')
        for run in v['runs']:
            out=Path(run['path']);assert all(sha(out/k)==h for k,h in run['files'].items())
            log=(r/f"run-{run['run']}.log").read_text(encoding='utf-8')
            assert f"PASS scope_checks={run['full_scope_checks']} label=formal" in log
        assert all(sha(r/'analysis-01'/k)==h for k,h in v['csv_files'].items())
        assert sha(r/'build/scale_formal.exe')==load(r/'build/binary.json')['sha256']
        assert (r/'build/scale_formal.cpp').read_bytes()==generated
        # Archive the unchanged core/old driver after rehashing; pre-run hashes already frozen.
        for k,h in old.items():
            dest=r/'source'/k;dest.parent.mkdir(parents=True,exist_ok=True)
            if not dest.exists():shutil.copyfile(P/k,dest)
            assert sha(dest)==h
        save(r/'old-source-hashes.json',old);shutil.copyfile(ROOT/'environment.json',r/'environment.json')
        peak=max(c['private_peak_sampled_bytes'] for c in commands);low=min(c['available_min_sampled_bytes'] for c in commands);gap=max(c['maximum_sample_gap_s'] for c in commands)
        summary=dict(status='passed',experiment=exp,dataset=ds,formal_workers=5,records=25000,queries=manifest['queries'],directories=manifest['directories'],raw_rows=v['timing_rows'],measurement_rows=v['measurement_rows'],warmup_rows=v['warmup_rows'],full_scope_checks=v['full_scope_checks'],unit_elapsed_s=status['elapsed_s'],private_peak_sampled_bytes=peak,minimum_available_sampled_bytes=low,maximum_sample_gap_s=gap,new_source_entries=source_entries,old_53_source_entries_unchanged_and_archived=True,worker_output_files_rehashed=sum(len(s['files']) for s in v['runs']),csv_hashes_match=True,protocol_and_fixture_match=True,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        save(r/'review-check.json',summary)
        per={(x['strategy'],x['group']):x for x in v['summary']}
        lines=[f'# {exp}：{ds.upper()} 25k纯目录正式实验','',
            '**可信状态：已运行并独立核验通过。** 当前独立目录工作负载的正式成绩，不是作者原协议、ANN质量或全文复现验收。','',
            f"实际单元时间：{status['started_utc']}–{status['finished_utc']}（UTC，香港+8小时），{status['elapsed_s']:.3f}秒，包含5次worker与1次核验器启动门禁。5/5独立进程，run0..4，每策略3预热+20测量；串行启动。",'',
            f"冻结输入25000条，含根{manifest['directories']}个真实目录（不含测试父）、{manifest['queries']}个两模式case。原始{v['timing_rows']}行，正式{v['measurement_rows']}、预热{v['warmup_rows']}；全部{v['full_scope_checks']}次原生完整集合核对通过。每pass五状态树/catalog/bitmap/invariants以及全部查询判定；Python独立元组Oracle、所有重复格位/空间状态/策略轮换与跨进程一致性通过。",'',
            '协议protocol.md；配置config.json；源/环境/flags/exe在source/、environment.json、build/，pre-run哈希source-hashes.json与准备目录old-53-source-hashes.json；原始数据run-0..4/，真实命令commands.json、各日志及monitor/preflight。后审查重新核验并归档旧53源码，原核心及旧实验不改。', '',
            f'资源采样：private最大{peak/(1<<20):.2f}MiB，available最低{low/G:.3f}GiB，实际最大间隔{gap*1000:.3f}ms。每个重型启动前连续20秒available≥4GiB，运行2GiB private/available阈值、600秒命令、1800秒单元和1GiB输出均通过。样本可能漏峰，不是OS配额或精确峰值。', '',
            '统计仅用pass3..22；下表微秒为5个独立进程各自均值的均值±样本SD，不把100次内部重复当100个独立进程，不宣称统计显著。逐run分位数/逐case路径、候选数、深度均在analysis-01/ CSV中；不删除空范围或慢点。', '',
            '| API/组 | PE-ONLINE μs | PE-OFFLINE μs | TrieHI μs |','|---|---:|---:|---:|']
        for group in ['build','query-recursive','query-local','move-large','merge-large','move-deep','merge-deep']:
            values=[]
            for s in ['PE-ONLINE','PE-OFFLINE','TrieHI']:
                x=per[(s,group)];assert x['processes']==5;values.append(f"{x['mean_us']:.4f} ± {x['sd_process_means_us']:.4f}")
            lines.append('| '+group+' | '+' | '.join(values)+' |')
        lines+=['','维护几何由独立判定器记录在analysis-01/verification.json；large/末端行为不同，不能只报总体最快。API计时不含独立核验，wall包含校验/析构另存；portable bytes不等于物理堆。所有查询按冻结case等权，递归与非递归分开，不以根请求或空请求权重差异解释全部算法差。', '',
            '输入/查询/维护集合与旧10k不同，不能将两组均值直接当严格规模增长率；不根据结果重选目录/维护/参数。本次不含phase、向量、ANN、nDCG或PG/Viking；原作者查询约束/DSM及全量缺口保留。完整分析CSV哈希、审查与最终检查见review-check.json、review.md、final-check.json。']
        (r/'record.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
        (r/'results.md').write_text('# 结果入口\n\n正式结果与边界统一在[record.md](record.md)；可计算汇总在[summary.csv](analysis-01/summary.csv)，逐进程[per-run.csv](analysis-01/per-run.csv)、逐case[per-case-run.csv](analysis-01/per-case-run.csv)。不复制第二份结果正文。\n',encoding='utf-8')
        (r/'review.md').write_text('''# 正式测量审查

当前会话自审，不声称外部审稿或独立代理审查。

- 预先冻结25k样本/查询/4维护，逐文件与前置02样本一致；两次源hash及metadata独立重读前置继续有效，正式前后source size/mtime核验由独立Oracle执行。无向量/qrels读取。
- 新生成驱动严格等于旧准入11项+正式合同2项替换；原API计时、五状态全集合/树/catalog/bitmap核对、10000时钟校准不变。Release优化且关闭ASan/phase；ASan仅在入口检查中使用。
- 正式前验证所有run0..4、双pass、WIKI Release/ASan答案与portable一致、与既有5k答案一致；四项错误原因合同和真实单元截止杀子进程测试通过。不是重跑原核心实验。
- 逐进程的run/pass/warmup/case、完整timing/space/wall格位、首pass摘要、全部pass原生完整集合均核对。预热单独留存不混统计；五独立子进程串行且顺序按run%3轮换，不声称五run完全平衡。
- 逐条遥测/启动20秒样本、600秒命令/1800秒包含门禁核验单元、输出大小检查；实际间隔≤250ms。样本不是精确峰值，未来运行仍须新门禁，不使用过去available作为保证。
- 逐worker五文件、所有CSV、协议/输入/新源归档及二进制hash重核验；旧53源码当前及归档一致，旧实验保留。证据review-check.json。
- 分析只使用正式pass，报告五进程均值SD、逐run/逐case和候选数，保留空范围/慢点/反例。不对不同N不同工作负载声称严格增长率，不把native总wall当API延迟，不把portable当物理堆，不将独立目录场景冒充原作者协议。

结论：当前获批25k纯目录正式矩阵通过；全文目标、ANN/原作者协议/真实类别与全量不因此关闭。下一步审查当前扩规模结论与已有报告衔接，不能自动扩大N或改算法。
''',encoding='utf-8')
        final=load(r/'final-check.json');final.update(post_review='passed',review_check_sha256=sha(r/'review-check.json'),old_sources_archived=True,record_sha256=sha(r/'record.md'),results_sha256=sha(r/'results.md'));save(r/'final-check.json',final)
        assert sum(f.stat().st_size for f in r.rglob('*') if f.is_file())<G
        summaries.append(summary)
    active=[]
    for proc in psutil.process_iter(['name','cmdline']):
        try:
            name=(proc.info['name'] or '').lower();cmd=' '.join(proc.info['cmdline'] or [])
            if name=='scale_formal.exe' or (name.startswith('python') and 'code/scale_formal/pipeline.py' in cmd):active.append(proc.pid)
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    assert not active
    save(ROOT/'final-review.json',dict(status='passed',units=summaries,total_formal_workers=10,total_timing_rows=sum(s['raw_rows'] for s in summaries),total_measurement_rows=sum(s['measurement_rows'] for s in summaries),total_full_scope_checks=sum(s['full_scope_checks'] for s in summaries),old_53_sources_unchanged=True,active_tasks=active))
    print(json.dumps(summaries,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
