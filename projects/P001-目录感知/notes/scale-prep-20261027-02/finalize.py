# -*- coding: utf-8 -*-
"""Post-run evidence audit and factual record. No experiment execution."""
import ast
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import psutil

P=Path.cwd();R=P/'notes/scale-prep-20261027-02';FIRST=P/'notes/scale-prep-20261027-01';G=1<<30
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def main():
    status=load(R/'status.json');assert status['status']=='passed'
    assert load(R/'final-check.json')['status']=='passed'
    commands=load(R/'commands.json');assert len(commands)==20
    old=load(P/'experiments/EXP-20261027-007/source-hashes.json');assert len(old)==53
    assert all(sha(P/k)==v for k,v in old.items())
    sources=load(R/'source-hashes.json');assert all(sha(P/k)==v and sha(R/'source'/k)==v for k,v in sources.items())
    spec=importlib.util.spec_from_file_location('whitelist',P/'code/scale_directory/generate.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    expected,changes=module.render((P/'code/wiki_experiment/directory.cpp').read_bytes());assert len(changes)==11
    for build in ['release','asan']:
        b=R/'builds'/build;info=load(b/'binary.json');assert sha(Path(info['path']))==info['sha256']
        assert (b/'scale_directory.cpp').read_bytes()==expected
        assert load(b/'scale_directory.changes.json')['source_sha256']==sha(P/'code/wiki_experiment/directory.cpp')
        shutil.copyfile(info['path'],b/'scale_directory.exe');assert sha(b/'scale_directory.exe')==info['sha256']
        flags=(b/'build.ninja').read_text(encoding='utf-8')
        assert ('/fsanitize=address' in flags)==(build=='asan')
        assert 'DIRECTORY_PHASE_DIAGNOSTICS' not in flags and 'DIRECTORY_ALLOCATION_DIAGNOSTICS' not in flags
    for p in (P/'code/scale_directory').glob('*.py'):ast.parse(p.read_text(encoding='utf-8'))
    source=load(R/'source-verification.json');assert source['status']=='passed' and source['vector_payload_bytes_read']==0
    assert load(R/'negative-contracts.json')['status']=='passed'
    assert len(load(R/'negative-contracts.json')['tests'])==6
    gaps=[];private=[];available=[]
    for c in commands:
        m=load(R/(c['name']+'-monitor.json'));assert m['violation'] is None
        assert c['exit_code']==c['expected_exit'] and c['elapsed_s']<=600
        assert m['private_peak_sampled_bytes']<=2*G and m['available_min_sampled_bytes']>=2*G
        samples=m['samples'];gap=max([b['elapsed_s']-a['elapsed_s'] for a,b in zip(samples,samples[1:])] or [0])
        assert gap==m['maximum_observed_sample_gap_s'] and gap<=.25
        gaps.append(gap);private.append(m['private_peak_sampled_bytes']);available.append(m['available_min_sampled_bytes'])
        gate=load(R/(c['name']+'-preflight.json'));ss=gate['samples']
        assert all(s['available_bytes']>=4*G and s['disk_free_bytes']>=10*G for s in ss)
        assert ss[-1]['elapsed_s']-ss[0]['elapsed_s']>=gate['required_stable_s']-.001
    rows=[];checks=0
    for ds in ['arxiv','wiki']:
        for n in [5000,25000]:
            v=load(R/f'verification-{ds}-{n}.json');assert v['status']=='passed'
            f=R/'fixtures'/f'{ds}-{n}';m=load(f/'manifest.json');first=load(FIRST/'fixtures'/f'{ds}-{n}'/'manifest.json')
            assert m['files']==first['files'],'input/geometry changed during resource repair'
            assert all(sha(f/k)==val for k,val in m['files'].items())
            if n==5000:assert len(v['runs'])==2 and v['runs'][0]['files']['answers.tsv']==v['runs'][1]['files']['answers.tsv']
            for run in v['runs']:
                out=P/run['output'];assert all(sha(out/k)==val for k,val in run['files'].items())
                c=next(c for c in commands if P/c['command'][2]==out and c['command'][-1]=='admission')
                checks+=run['scope_checks']
                rows.append(dict(dataset=ds,n=n,queries=m['queries'],directories=m['directories'],max_depth=m['max_depth'],build='asan' if 'asan' in out.name else 'release',checks=run['scope_checks'],wall_s=c['elapsed_s'],private_mib=c['private_peak_sampled_bytes']/(1<<20)))
    active=[]
    for p in psutil.process_iter(['pid','name','cmdline']):
        try:
            name=(p.info['name'] or '').lower();cmd=' '.join(p.info['cmdline'] or [])
            if name in ['scale_directory.exe','cl.exe','ninja.exe','cmake.exe'] or (name.startswith('python') and 'code/scale_directory/pipeline.py' in cmd):active.append(p.info)
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    assert not active,'active admission/build process remains'
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=P,text=True).strip();assert head==status['git_head']
    git=subprocess.check_output(['git','status','--short'],cwd=P);(R/'git-status-final.txt').write_bytes(git)
    (R/'git-diff-final.patch').write_bytes(subprocess.check_output(['git','diff','--binary'],cwd=P))
    summary=dict(status='passed',finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),workers=6,scope_checks=checks,negative_contracts=6,fixtures=4,release_asan_pairs=2,source_records_rechecked={ds:source[ds]['records'] for ds in ['arxiv','wiki']},old_53_sources_unchanged=True,new_sources_and_archive_unchanged=True,generated_source_exact_11_whitelist=True,current_and_archived_binaries_match=True,all_output_hashes_match=True,protocol_unchanged_across_resource_repair=True,initial_fixtures_unchanged=True,maximum_sample_gap_s=max(gaps),private_peak_all_commands_bytes=max(private),minimum_available_all_commands_bytes=min(available),output_bytes=sum(f.stat().st_size for f in R.rglob('*') if f.is_file()),active_tasks=[],git_head=head,formal_runs=0,vector_payload_bytes_read=0,initial_monitoring_deviation='Initial 01 automatic passed overridden by audit for strict resource admission; 342ms max; initial evidence preserved; final valid admission 02.',rows=rows)
    assert summary['output_bytes']<G
    # Original automated forecast omitted the stable startup windows. Retain it,
    # add five worker + one verifier windows before the margin, do not hide this correction.
    forecasts=[]
    for original in load(R/'budget-forecast.json')['forecasts']:
        f=original.copy();f['preflight_windows_s']=6*20
        f['matrix_without_preflight_s']=f['matrix_s'];f['matrix_s']+=f['preflight_windows_s']
        f['screen_1_5x_s']=1.5*f['matrix_s'];f['matrix_budget_pass']=f['screen_1_5x_s']<=1440
        f['assumptions']+=' Reviewed correction: add six stable 20s startup windows inside each dataset unit before 1.5x margin; preparation/build not part of formal unit.'
        forecasts.append(f)
    save(R/'budget-reviewed.json',dict(status='estimate_only',correction='Original budget-forecast.json excluded 120s of six stable startup windows; retain original and use this reviewed scenario.',forecasts=forecasts))
    summary['reviewed_budget_pass']=all(f['matrix_budget_pass'] and f['worker_budget_pass'] and f['admission_memory_pass'] for f in forecasts)
    save(R/'review-check.json',summary)
    lines=['# SCALE-PREP-01：纯目录参数化与新规模准入记录','',
        '可信状态：**最终有效准入已验证通过**。本记录是软件/资源准入，不是SCALE-02正式测量，不比较性能胜负。', '',
        f"实际时间：{status['started_utc']}–{status['finished_utc']}（UTC，香港时间加8小时）。Git main/{head}，保留既有未提交评估/文档增量，本轮未提交、推送、重置或清理。",'',
        '冻结协议`../scale-prep-protocol-20261027.md`；命令`commands.json`；入口`../../code/scale_directory/README.md`。资源修正后的源码/协议快照在source/，生成C++/11项替换/flags/缓存/实际exe在builds/。只读ARXIV全量time绑定和WIKI真实paths，不读向量、qrels或query内容。','',
        '| 数据 | N | 目录（未加测试父） | 查询两模式合计 | 构建 | 完整集合检查 | 进程总秒 | private采样MiB |',
        '|---|---:|---:|---:|---|---:|---:|---:|']
    for x in rows:lines.append(f"| {x['dataset']} | {x['n']} | {x['directories']} | {x['queries']} | {x['build']} | {x['checks']} | {x['wall_s']:.3f} | {x['private_mib']:.2f} |")
    lines+=['',f'合计{checks}次原生完整集合比较；每个worker为3策略/0预热/1pass，五个连续状态。4份Python独立路径元组核验、2组Release/ASan输出/portable一致性、6项指定原因拒绝测试、两源全量hash/选样独立重读均通过。WIKI 5k深29缺深31层按协议记不适用，25k覆盖全部指定层且深31；不是按结果换样。', '',
        f'资源：每重型命令前连续20秒available≥4GiB，短合同即时检查；全部运行采样available最低{min(available)/G:.3f}GiB，private合计最大{max(private)/(1<<20):.2f}MiB，命令均<600s、证据<1GiB，实际采样最大间隔{max(gaps)*1000:.3f}ms≤250ms。private按子进程树求和，样本可能漏峰，不能当OS配额或精确峰值；短ARXIV命令尤需保留此限制。', '',
        '首次记录../scale-prep-20261027-01/正确性通过但监控实际最大342ms，严格门禁不接受其自动passed；100ms整循环修正后先定向核验、再在本目录必要重做准入。两次fixture全部内容hash一致，原始结果/失败审查保留。未重跑004–008。', '',
        '| 25k预算场景 | 单worker秒 | 5进程+核验+启动秒 | 1.5倍筛查秒 | ≤1440秒 |',
        '|---|---:|---:|---:|---|']
    for f in forecasts:lines.append(f"| {f['dataset']} | {f['worker_s']:.2f} | {f['matrix_s']:.2f} | {f['screen_1_5x_s']:.2f} | {'通过' if f['matrix_budget_pass'] else '未通过'} |")
    lines+=['','这是setup+23×单次三策略完整pass（含校验/析构）+真实退出残差的估计，按5独立worker加5倍本次单输出核验器时长；审查补入5个worker及1个核验器共120秒连续启动门禁，再加1.5倍时间筛查，并要求≤1440秒以保留1800秒硬预算的20%裕量。原自动budget-forecast.json漏了这120秒，保留原件，最终采用budget-reviewed.json。不是正式测量或长期内存保证；正式多进程输出解析成本尚须在其入口核验，不能把5倍核验场景写成严格上界。','',
        '完成边界：SCALE-PREP-01当前25k纯目录软件/资源准入通过；SCALE-01父任务仍待正式矩阵/预算决定，SCALE-02未启动。当前binary故意只接受admission单pass；未来正式run轮换/重复/输出检查需单独入口及准入。原作者查询目录/DSM、真实类别、nDCG、PG/Viking和全量仍未解决。','',
        '下一步建议：批准并冻结两数据集25k纯目录默认各5独立进程、3预热20测量的SCALE-02矩阵与停止预算，复用已冻结fixture；准备正式入口并核验run轮换和所有重复格位后才运行。启动前仍需重新连续采样，不能复用本次available数值作为未来保证。']
    (R/'record.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (R/'review.md').write_text('''# SCALE-PREP-01审查

本轮采用源码逐项检查、独立判定器及原始输出/遥测复核；这是当前会话自审，没有声称外部或独立代理审查。

- **实现忠实**：007的53项旧源码/协议当前hash匹配，含原三核心、第三方、旧驱动与判定器。新生成源严格等于冻结旧驱动的11项允许替换；API计时边界/完整集合检查、10000时钟次数均保留。新增预算pass包含校验/析构，不冒充API延迟。
- **数据与覆盖**：全局ID等间隔、严格递增/范围及dense映射；两源流式完整hash和独立选样重读，fixture四份hash跨资源修正一致。独立核验重新推导深度/候选数/fanout、锚点与连续维护合法性；五状态树/条目/bitmaps统计和查询格位无缺失。缺失层明确不适用。WIKI是真实语料目录，测试查询/维护属于项目协议。
- **独立性**：Python使用元组前缀枚举，不调用生产路径helper或prepare；C++逐查询完整集合比较使用原独立Oracle。Python摘要是额外核验，不把摘要哈希当作完整集合的唯一证据。不导入NumPy、不读取向量或qrels，不引入Local捷径。
- **负向合同/构建**：非法shape、行数不符、global重复/逆序/越界和非法查询mode共6项，均需exit1与指定FAIL标记。Release关闭诊断/ASan，ASan实际flags覆盖driver/oracle/core/CRoaring；5k跨构建答案与portable一致。
- **发现并纠正的问题**：初次监控200ms sleep加循环开销导致342ms间隔，审查推翻其严格资源达标结论，证据未覆盖。改为100ms整循环目标、保存实际最大间隔并加最终间隔断言；定向复核后必要重做本次小范围准入。本目录20条命令均实际≤250ms，见review-check.json。操作系统仍可能延迟未来采样，因此不能保证每次启动自动达标。
- **资源和推断边界**：连续20秒启动门槛、实际采样/所有资源阈值逐条复核；样本不等于精确峰值。单pass不能证明23pass长期常驻/缓存或正式解析成本，预算只作带明确假设的筛查；正式执行需运行时停止门禁。WIKI large维护在该样本没有复杂内部冲突覆盖，不能外推全部DSM。
- **预算审查修正**：自动预算未计5个worker与1个核验器的连续启动窗口；不覆盖原预算，另在budget-reviewed.json加入120秒再乘1.5，最终提案采用该值。准备/编译不混入正式测量单元；若正式协议再增加步骤，必须补入其预算。
- **成果保护**：旧46与007扩展53源码均未变；新输出独立目录，首轮偏差、修正与二进制hash留存。最终有效exe另复制归档且hash匹配。原正式实验/原始数据不改，不提交Git，不安装依赖。

结论：本次SCALE-PREP-01当前25k纯目录准入可关闭；原始协议缺口及全文复现不关闭。下一步仅建议审定SCALE-02矩阵/预算，再准备正式入口；本轮没有自动运行5进程正式实验。
''',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
