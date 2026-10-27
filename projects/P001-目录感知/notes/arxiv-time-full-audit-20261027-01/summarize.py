"""Summarise audited facts only; never runs an index or scans vectors."""
import collections,hashlib,json
from pathlib import Path
base=Path(__file__).resolve().parent;run=base/'run-01'
m=json.loads((run/'manifest.json').read_text(encoding='utf-8'));v=json.loads((run/'verification.json').read_text(encoding='utf-8'))
assert m['status']==v['status']=='passed' and m['counts']['records']==v['records_verified']
dirs=json.loads((run/'directory-counts.json').read_text());queries=json.loads((run/'time-query-coverage.json').read_text())
years={int(r['path'].strip('/')):r['recursive'] for r in dirs if r['path'].count('/')==2}
months=[r['path'] for r in dirs if r['path'].count('/')==3];ordered=sorted(int(p.split('/')[1])*12+int(p.split('/')[2])-1 for p in months)
missing=sorted(set(range(ordered[0],ordered[-1]+1))-set(ordered))
summary={'status':'verified','records':v['records_verified'],'id_range':[m['id_min'],m['id_max']],
 'directories_including_root':len(dirs),'year_directories':len(years),'month_directories':len(months),'maximum_depth':2,
 'first_month':f'{ordered[0]//12}/{ordered[0]%12+1}/','last_month':f'{ordered[-1]//12}/{ordered[-1]%12+1}/',
 'missing_years_within_observed_span':sorted(set(range(min(years),max(years)+1))-set(years)),
 'missing_months_within_observed_span':[f'{x//12}/{x%12+1}/' for x in missing],
 'numeric_month_alias_count':len(months)-len(set(ordered)),
 'leading_zero_month_spellings':[p for p in months if p.split('/')[2]!=str(int(p.split('/')[2]))],
 'time_constraints':len(queries),'constraint_depth_counts':dict(collections.Counter(r['path'].count('/')-1 for r in queries)),
 'missing_constraint_directories':sum(not r['exists'] for r in queries),'zero_direct_member_constraints_if_nonrecursive':sum(r['direct_members']==0 for r in queries),
 'metadata_sha256':v['metadata_sha256'],'bindings_sha256':v['bindings_sha256'],'bindings_bytes':(run/'bindings.tsv').stat().st_size,
 'metadata_parse_seconds':m['elapsed_seconds'],'independent_verification_seconds':v['elapsed_seconds'],
 'full_vector_integrity_checked':False,'corpus_vector_bytes_read':4,'vector_header_bytes_read':4,'vector_payload_bytes_read':0,'full_scale_index_or_performance_run':False}
(run/'coverage-summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
for name,expected in [('audit.py',m['script_sha256']),('verify.py',v['script_sha256'])]:
    assert hashlib.sha256((base/name).read_bytes()).hexdigest()==expected
    target=run/name
    if target.exists():assert target.read_bytes()==(base/name).read_bytes()
    else:target.write_bytes((base/name).read_bytes())
text=f'''# DATA-TIME-FULL-01 — 全量 ARXIV 时间目录核查

日期：2026-10-27。用户已明确授权全量metadata只读核查，原始数据从未以写模式打开；未加载全量向量，未建索引或运行性能。不是作者工作负载恢复，也不是全文数据完整性通过声明。

## 已验证的结果

- 完整解析482,867,712字节JSON，验证数组闭合/EOF/字段重复和语法，读取缓冲峰值约1Mi字符；第一遍{m['elapsed_seconds']:.3f}秒，独立复核{v['elapsed_seconds']:.3f}秒。未安装依赖，未将全部JSON对象装入内存。
- 共{v['records_verified']:,}条记录，ID为0–{m['id_max']:,}；逐条ID等于行号，因此连续、唯一，无重复/缺失/越界，所有time字段合法。主审计用352,256字节稀疏位图核对ID覆盖；独立验证逐条重新证明。
- {len(years)}个年份目录、{len(months)}个月份目录，加根共{len(dirs)}个目录，最大深度2。条目全部直接绑定到月份；根/年份只有递归成员。
- 输出完整bindings.tsv，共{(run/'bindings.tsv').stat().st_size:,}字节，规则只补首尾斜杠，保留月份原拼写、不改类别。前10,000个原始对象与旧快照一致，前10,000条绑定字节与旧冻结输入完全相同。
- 两种解析方式（增量JSONDecoder与按实际缩进独立分帧后json.loads）逐条核对全部2,763,543条映射，目录计数和完整metadata SHA-256一致，读取前后size/mtime未变。不是只对照摘要或抽样。
- 元数据ID范围与fvecs首维1024及文件长度推得的2,763,543行结构相容，余数0。向量仅读4字节头，载荷读0；没有验证每行维度、有限值、向量内容或语义ID对应。
- 混合约束中501条time目录全部存在：266个年份、235个月份；未读取GT，也未据真值选择数据。递归/非递归模式没有恢复，不能把目录存在称为检索质量通过。

## 新发现：1995年覆盖缺口

观测范围为1991/7至2025/7，期间缺1995年全部12个月；其余没有数值月份别名或前导零变体。该事实来自全量文件，不是抽样遗漏。现有发布README快照和加载审查没有提供1995年过滤原因，尚待核对发布方生成/过滤说明。

编号 **GAP-TIME-COVERAGE-01**：原因待确认；不能据此认定本地文件损坏或发布方错误，也不能填造1995数据、改时间或删除其他记录。全量metadata字段/映射审计完成，不等于已证明发布数据覆盖所有arXiv论文。该缺口不妨碍在“当前实际发布文件”上定义有标注的时间目录实验，但不能声称恢复作者未提供的完整协议。

## 证据与命令

```powershell
python notes/arxiv-time-full-audit-20261027-01/audit.py --self-test
python notes/arxiv-time-full-audit-20261027-01/audit.py --project . --output notes/arxiv-time-full-audit-20261027-01/run-01
python notes/arxiv-time-full-audit-20261027-01/verify.py --self-test
python notes/arxiv-time-full-audit-20261027-01/verify.py --project . --output notes/arxiv-time-full-audit-20261027-01/run-01
```

上述两次实际扫描/复核退出码0。已有目录拒绝覆盖，若重跑必须使用新run。日志audit-run-01.log、verify-run-01.log；run-01内保存manifest、verification、完整绑定、目录计数、time-query-coverage、anomalies（本次为空）、coverage-summary及两份执行脚本快照。

完整metadata SHA-256：`{v['metadata_sha256']}`。这是本地内容校验，不是发布方checksum匹配。

完整bindings SHA-256：`{v['bindings_sha256']}`。

## 本任务完成条件与后续

全量记录/ID/time、目录分布、完整清单、旧样本兼容、结构行数、输入不变及独立复核均已完成，DATA-TIME-FULL-01可关闭。父任务DATA-01/SPEC-01仍进行中：真实类别直接归属、多归属DSM、WIKI约束、作者维护序列及质量协议缺口保留。

下一步先核对GAP-TIME-COVERAGE-01来源，并以本次实际绑定和目录分布制定更大规模时间目录实验的协议/资源估算（SCALE-01）。需要考虑独立oracle全目录枚举成本，不能只按小样本内存线性推算。未授权的扩规模性能矩阵不启动，旧10,000条协议不静默替换为全量数据。
'''
(base/'report.md').write_text(text,encoding='utf-8')
print(json.dumps(summary))
