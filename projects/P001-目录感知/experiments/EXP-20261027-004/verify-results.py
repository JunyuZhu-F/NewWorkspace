"""Independent completeness checks and descriptive default-core report; no reruns."""
import collections
import hashlib
import itertools
import json
import math
from pathlib import Path

root = Path(__file__).resolve().parent
project = root.parent.parent
def read(name):
    return [json.loads(s) for s in (root / name).read_text(encoding='utf-8').splitlines() if s.strip()]
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def identity(r):
    return (r['run'], r['input'], r['subload'], r['strategy'], r['instrumented'])
workloads = [('figure2','build'),('figure2','dsq'),('figure2','move'),('figure2','merge'),('time','build'),('time','dsq'),('time','dsm')]
expected = {(n,i,w,s,b) for n in range(5) for i,w in workloads for s in ['pe_online','pe_offline','trie_hi'] for b in (False,True)}
order = read('run-order.jsonl')
process = read('raw/process.jsonl')
assert len(order) == len(process) == 210
assert {identity(r) for r in order} == {identity(r) for r in process} == expected
assert all(r['status'] == 'passed' and r['returncode'] == 0 for r in order)
assert all(r['status'] == 'passed' and r['correctness_checks'] > 0 for r in process)
assert json.loads((root/'run-status.json').read_text())['status'] == 'complete'
snap = json.loads((root/'source/hashes.json').read_text())
for name, digest in snap['files'].items():
    assert sha(root/'source'/name) == digest, name
    current = project/name if name.startswith('code/') else project/'notes/benchmark-fixtures-20261026-01'/Path(name).name
    assert sha(current) == digest, str(current)
config = json.loads((root/'config.json').read_text())
combined=hashlib.sha256(''.join(f'{k}\0{v}\n' for k,v in sorted(snap['files'].items())).encode()).hexdigest()
assert combined==snap['source_snapshot_hash']==config['source_snapshot_hash']
assert sha(root/'protocol.md') == config['protocol_sha256'] == sha(project/'notes/benchmark-protocol.md')
assert sha(project/'notes/benchmark-fixtures-20261026-01/manifest.json') == config['fixture_manifest_sha256']
assert all(r['source_hash'] == config['source_snapshot_hash'] for r in process)
summary = json.loads((root/'summary.json').read_text())
raw = {k:read('raw/'+k+'.jsonl') for k in ('build','dsq','dsm','space','timing')}
counts = {k:len(v) for k,v in raw.items()}
assert counts == dict(build=1380,dsq=62100,dsm=3450,space=1380,timing=210), counts
assert {identity(r) for r in raw['timing']} == expected
assert all(r['clock_is_steady'] and r['empty_interval_n']==10000 for r in raw['timing'])
for kind, rows in raw.items():
    if kind=='timing': continue
    groups = collections.defaultdict(list)
    for r in rows:
        assert r['source_hash']==config['source_snapshot_hash']
        assert r['warmup'] == (r['iteration']<3)
        assert r['experiment']==root.name
        groups[identity(r)].append(r)
    relevant = {job for job in expected if (job[2] in ('build',) if kind in ('build','space') else job[2]=='dsq' if kind=='dsq' else job[2] in ('move','merge','dsm'))}
    assert set(groups)==relevant
    for job, group in groups.items():
        per_iteration = (22 if job[1]=='figure2' else 68) if kind=='dsq' else (3 if job[2]=='dsm' else 1)
        assert collections.Counter(r['iteration'] for r in group)=={i:per_iteration for i in range(23)}, (kind,job)
        if kind=='dsq':
            keys = [(r['iteration'],r['path'],r['recursive']) for r in group]
            assert len(set(keys))==len(keys)
            for r in group:
                assert r['work_counters_status']==('collected' if job[-1] else 'not_collected_in_default_core')
        if kind=='dsm':
            assert all(r['accepted']==(r['source']!='/1992/8/') for r in group)
    field = {'build':'build_ns','dsq':'total_ns','dsm':'total_ns','space':'roaring_portable_bytes'}[kind]
    keys = ['input','strategy','subload','instrumented'] + (['path','recursive'] if kind=='dsq' else ['operation','source','target_or_new_parent','accepted'] if kind=='dsm' else [])
    pooled = collections.defaultdict(list)
    for r in rows:
        if not r['warmup']: pooled[tuple(r[k] for k in keys)].append(r[field])
    for entry in summary[kind]:
        values = sorted(pooled[tuple(entry[k] for k in keys)])
        assert entry['pooled']['n']==len(values)
        assert math.isclose(entry['pooled']['mean'],sum(values)/len(values),rel_tol=1e-12)
        for label,p in [('p90',.9),('p95',.95),('p99',.99),('p99_9',.999)]:
            assert entry['pooled'][label]==values[math.ceil(p*len(values))-1]
out = {'status':'passed','processes':210,'exact_job_matrix':True,'raw_counts':counts,'source_snapshot_hash':config['source_snapshot_hash'],
       'snapshot_files_checked':len(snap['files']),'protocol_and_fixture_hashes_match':True,'all_23_iterations_present':True,
       'summary_means_and_nearest_rank_quantiles_recomputed':True,'separate_diagnostic_instrumentation':True}
lines=['# DIR-01 实测结果', '', '仅适用于本项目 Windows 单父目录诊断工作负载，不是作者原始负载或原版数值复现。', '',
       '210/210 进程成功；独立核对矩阵、23 次迭代、源码/输入/协议哈希及汇总均值和 nearest-rank 分位数通过。', '',
       '下表只使用默认核心，3 次预热已排除。时间单位为微秒；均值来自原始测量，未减计时开销。', '',
       '| 输入/操作 | PE-ONLINE 均值 | PE-OFFLINE 均值 | TrieHI 均值 | 每方案 N |', '|---|---:|---:|---:|---:|']
strategies=['pe_online','pe_offline','trie_hi']
for inp in ['figure2','time']:
    for kind in ['build','dsq','dsm']:
        rows=[r for r in raw[kind] if r['input']==inp and not r['instrumented'] and not r['warmup']]
        subgroups=collections.defaultdict(list)
        for r in rows:
            label=('DSQ recursive' if r['recursive'] else 'DSQ nonrecursive') if kind=='dsq' else ('build' if kind=='build' else r['operation']+(' accepted' if r['accepted'] else ' rejected'))
            subgroups[label].append(r)
        for label, rr in subgroups.items():
            values=[[r['build_ns' if kind=='build' else 'total_ns'] for r in rr if r['strategy']==s] for s in strategies]
            lines.append('| '+inp+' '+label+' | '+' | '.join(f'{sum(v)/len(v)/1000:.4f}' for v in values)+' | '+str(len(values[0]))+' |')
lines += ['', 'DSQ 表为同一输入全部路径的等权合并描述；逐路径分布、各进程均值和 P90/P95/P99/P99.9 见 summary.json。重复 sweep 不能当独立实验，小样本 P99.9 不稳定。', '',
          '空间包含 Roaring portable bitmap 大小及进程 working set/private/peak，不是完整堆或完整序列化索引大小。catalog 已包含在公开维护总延迟，独立 catalog/阶段耗时未采集，不能据此给出目录净时间。', '',
          '失败记录 EXP-20261027-001/002/003 保留；正式矩阵只使用修复后的 004，不混入失败或 ASan 数据。']
lines += ['', '## 当前观测及限制', '',
          '- time 递归 DSQ：TrieHI 2.7203 µs、PE-OFFLINE 2.6992 µs、PE-ONLINE 6.5276 µs；TrieHI 未优于 PE-OFFLINE 的该组均值。',
          '- time 非递归 DSQ：PE-ONLINE 2.4195 µs，TrieHI 5.4071 µs；未出现 TrieHI 全面占优。',
          '- time 成功 MOVE：PE-ONLINE 6.4590 µs，TrieHI 6.9070 µs；成功 MERGE 则分别为 207.2880 和 162.5300 µs。这是特定操作序列的观测，不能推断所有树形或规模。',
          '- DIR-01 冻结矩阵运行及正确性/完整性验证已完成；OBJ-03 完整成本分解仍缺独立 catalog/目录净耗时及完整逻辑 live bytes，不把矩阵成功等同最终目标验收。', '',
          '| 初始空间：输入/方案 | 目录数 | catalog 条目 | Roaring portable bytes |', '|---|---:|---:|---:|']
for inp,s in itertools.product(['figure2','time'],strategies):
    rr=[r for r in raw['space'] if r['input']==inp and r['strategy']==s and not r['instrumented'] and not r['warmup']]
    sizes={r['roaring_portable_bytes'] for r in rr}
    assert len(sizes)==1
    lines.append(f"| {inp}/{s} | {rr[0]['directory_count']} | {rr[0]['catalog_entry_count']} | {next(iter(sizes))} |")
memory_limits={'max_private_bytes':max(r['private_bytes'] for r in raw['space']),
               'max_peak_working_set_bytes':max(r['peak_working_set_bytes'] for r in raw['space']),
               'min_system_available_physical_bytes_at_space_samples':min(r['system_available_physical_bytes'] for r in raw['space'])}
out['sampled_memory']=memory_limits
out['binary_sha256']={name:sha(project/'code/build-Release'/name) for name in ['directory_benchmark.exe','directory_benchmark_instrumented.exe']}
out['timing_empty_interval_mean_ns_range']=[min(r['empty_interval_mean_ns'] for r in raw['timing']),max(r['empty_interval_mean_ns'] for r in raw['timing'])]
(root/'independent-verification.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
(root/'results.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(out))
