# -*- coding: utf-8 -*-
"""Verify frozen evidence and write factual run records after successful matrices."""
import datetime
import hashlib
import json
import csv
import struct
from pathlib import Path

P=Path.cwd();HERE=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')

def main():
    assert load(HERE/'status.json')['status']=='passed'
    checks=[]
    for exp,kind in [('EXP-20261027-007','directory'),('EXP-20261027-008','search')]:
        root=P/'experiments'/exp;state=load(root/'status.json');assert state['status']=='passed'
        for n,h in load(root/'source-hashes.json').items():
            assert sha(P/n)==h and sha(root/'source'/n)==h,n
        protocol=sha(root/'protocol.md');assert protocol==sha(P/'notes/wiki-independent-protocol-20261027.md')
        reports=list(root.glob('verification-*.json'));assert len(reports)==(2 if kind=='directory' else 1)
        nfiles=0;rows=0
        for r in reports:
            report=load(r);assert report['status']=='passed' and report['formal'] and len(report['workers'])==5
            rows+=report['raw_rows']
            for w in report['workers']:
                for n,h in w['files'].items():assert sha(P/w['output']/n)==h;nfiles+=1
        fixture=HERE/'fixture';manifest=load(fixture/'manifest.json')
        for n,h in manifest['files'].items():assert sha(fixture/n)==h,n
        for n,info in manifest['inputs'].items():
            stat=(P/'dataset/raw/WIKI-Dir'/n).stat();assert (stat.st_size,stat.st_mtime_ns)==(info['size'],info['mtime_ns'])
        old_wiki=load(P/'notes/wiki-preparation-20261027-01/run-01/report.json')
        selected=load(fixture/'sample.json');sample_hash=hashlib.sha256()
        with (fixture/'corpus.fvecs').open('rb') as f:
            for row in selected:sample_hash.update(struct.pack('<Q',row['global_id'])+f.read(4100))
            assert not f.read(1)
        assert sample_hash.hexdigest()==old_wiki['sample']['vectors']['row_and_record_sha256']
        assert sha(fixture/'queries.fvecs')==old_wiki['small_file_sha256']['dbpedia_dir_2m_query_vectors.fvecs']
        commands=[json.loads(x) for x in (root/'commands.jsonl').read_text(encoding='utf-8').splitlines()]
        assert all(x['exit_code']==0 for x in commands)
        events=[x for x in commands if x['label'].startswith('run-')]
        assert len(events)==(10 if kind=='directory' else 5)
        expected_labels={f'run-{mode}-{run}' for mode in (('default','phase') if kind=='directory' else ('search',)) for run in range(5)}
        assert {x['label'] for x in events}==expected_labels
        supplementary_rows=0
        for event in events:
            expected_run=int(event['label'].rsplit('-',1)[1]);assert int(event['command'][3])==expected_run
            output=P/event['command'][2];name='timings.tsv' if kind=='directory' else 'timings.csv'
            with (output/name).open(encoding='utf-8',newline='') as f:
                for row in csv.DictReader(f,delimiter='\t' if kind=='directory' else ','):
                    assert int(row['run'])==expected_run;supplementary_rows+=1
        assert supplementary_rows==rows
        cache=(root/'CMakeCache.txt').read_text(encoding='utf-8')
        assert 'CMAKE_BUILD_TYPE:STRING=Release' in cache and 'DIRECTORY_ENABLE_ASAN:BOOL=OFF' in cache
        provenance=load(root/'analysis-01/provenance.json')
        for name,h in provenance['source_reports'].items():assert sha(root/name)==h
        for name,h in provenance['exports'].items():assert sha(root/'analysis-01'/name)==h
        peak=max(x['peak_private_bytes_sampled'] for x in events);available=min(x['minimum_available_bytes'] for x in events)
        check=dict(status='passed',finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            formal_workers=len(events),raw_rows=rows,measurement_rows=rows*20//23 if kind=='directory' else rows,warmup_rows_recorded=rows*3//23 if kind=='directory' else 0,worker_output_files_rehashed=nfiles,
            run_labels_and_all_raw_run_ids_rechecked=True,export_provenance_rehashed=True,
            source_entries_rehashed=len(load(root/'source-hashes.json')),protocol_sha256=protocol,
            original_006_sources_unchanged=True,raw_vector_size_mtime_unchanged=True,
            old_wiki_sample_vector_records_match=True,
            peak_private_bytes_sampled=peak,minimum_available_bytes_sampled=available,
            output_bytes_at_check=sum(x.stat().st_size for x in root.rglob('*') if x.is_file()),
            published_query_constraints_recovered=False,ndcg_reported=False,full_scale_executed=False,
            complete_reproduction_claimed=False)
        save(root/'final-check.json',check);checks.append(dict(experiment=exp,**check))
        title='WIKI独立目录性能' if kind=='directory' else 'WIKI独立L2/IVF质量—总延迟'
        text=f'''# {exp} — {title}

状态：完成当前独立小规模分支，{len(events)}/{len(events)}正式进程退出0，{rows}条原始计时核验通过，其中正式测量{check['measurement_rows']}条、保留的预热记录{check['warmup_rows_recorded']}条。最终入口status.json、verification-*.json、final-check.json；结果表及可重绘CSV在results.md、analysis-01/。非作者原始工作负载，不关闭原论文数值对齐或全量目标。

## 授权、协议和版本

用户明确要求按独立协议执行、审查并更新文档；不等待作者联系。启动前协议notes/wiki-independent-protocol-20261027.md已冻结（正式副本protocol.md），实验已登记EXPERIMENTS。Git基线be59bbccb9e3f8e283328f453643b7d50211736d加保留的未提交成果；实际source/和source-hashes.json为源码依据，environment.json包含现场与Git状态，不能只用HEAD代表运行源码。原006的46源码未改，未重跑ARXIV。

本轮复用WIKI-DATA/CHECK的10000等间隔global ID样本，不按qrels或测量结果选样；源向量只读抽取这些记录及456条query。query metadata为空的描述/文件不一致保留，用户确认网盘文件也为空；本项目没有补造作者约束。

## 入口与真实运行

项目根使用D:/anaconda3/python.exe -B code/wiki_experiment/pipeline.py --stage {kind} --preparation notes/wiki-independent-preparation-20261027-01 --experiment {exp}。该命令已执行，不可覆盖既有实验目录；后续重跑必须另选EXP并登记。

科学准入证据见notes/wiki-independent-preparation-20261027-01/：新目录默认/phase及检索包装器Release/ASan均通过独立核验。原后端前缀逐字节相同，检索包装器仅调整456/912形状和合同标签，生成差异由pipeline.generated断言核查。三方案算法无修改，固定样本旧WIKI准入未重跑。

正式阶段从{state['started_utc']}到{state['finished_utc']}（UTC；香港时间+8小时），不是查询延迟。commands.jsonl逐条保存真实命令、退出码、时间、观测资源，run-*.log及每秒monitor保存原过程。build flags及CMakeCache已快照，Release正式计时关闭ASan。默认/phase分池；原始重复值、候选和质量数据不筛选。

资源门禁：单进程600秒、矩阵1800秒、private≤2GiB、available≥2GiB、输出≤1GiB。本次正式worker按每秒采样观测private最大{peak}字节、available最小{available}字节，未触发门禁。采样值不是精确峰值/索引独占；核验器也有独立内存开销，不能把worker样本当整轮最大内存。结果规模见final-check，不安装/修改依赖。

## 核验和结论边界

独立Python核验源区域、目录选择/哈希配对/操作规则、候选状态、模型/排名（检索）、全部重复格位、统计与计时边界；全部worker输出、当前源码及归档快照、fixture哈希在收尾再次核对。C++测量过程每次比较完整候选/结果；目录维护后全树/catalog/bitmap校验。程序运行时间不作为论文成绩。

本轮不报告nDCG：均匀样本仅46条查询有标注，未标注不等于不相关。查询目录、维护序列与距离/后端都是已声明项目约定，不能称为作者原始设置；原型IVF不是Viking或优化倒排实现。全部实测数值、反例、分位数和逐run差异见results.md及CSV，不作全面加速/显著性/尾部稳定性声明。核心目录正确不等于整篇论文复现成功。
'''
        if kind=='directory':text+='\n目录专属：58个两模式case、连续4项MOVE/MERGE，默认/phase各5进程，每pass从相同初始树重建；3预热20测量。catalog纳入默认API总量，直接catalog时间只来自phase，不做跨构建相减。portable字节仅位图序列化大小，不是完整树/catalog空间或物理堆；本轮没有额外allocation追踪。\n'
        else:text+='\n检索专属：912case、k10、exact和nprobe1/4/16，5进程×3预热20测量。平方L2、不归一化、16中心/seed42/8次Lloyd；子集目录内精确top10，空GT质量null而延迟保留。总量等于目录/ID转换/后端三个直接区间之和；加载/建树/聚类构建/输出及最后临时集合释放不在其中。质量相同不代表CPU每次耗时相同，不能把全部总差归因目录算法。\n'
        (root/'record.md').write_text(text,encoding='utf-8')
    for n,h in load(P/'experiments/EXP-20261027-006/source-hashes.json').items():assert sha(P/n)==h,n
    old=load(P/'experiments/EXP-20261027-006/verification.json');old_files=0
    for w in old['workers']:
        for n,h in w['files'].items():assert sha(P/w['output']/n)==h;old_files+=1
    save(HERE/'final-check.json',dict(status='passed',experiments=checks,old_006_worker_files_rehashed=old_files,core_46_unchanged=True))
    print(json.dumps(checks))
if __name__=='__main__':main()
