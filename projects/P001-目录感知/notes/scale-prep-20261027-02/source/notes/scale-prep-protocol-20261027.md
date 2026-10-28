# SCALE-PREP-01 — 纯目录参数化与准入冻结协议

2026-10-27，用户授权按已说明下一步执行、审查并更新文档。本轮范围仅隔离实现与准入，不是SCALE-02，不跑5进程/20测量正式矩阵，不新增正式EXP。

## 输入与选择

- ARXIV-time使用已审计全量bindings.tsv，WIKI使用原corpus_paths.json；原文件只读、源hash/size/mtime绑定。每数据集分别N=5000、25000，ID为floor(i*(total-1)/(N-1))，非嵌套采样；保持global/dense映射与完整路径。
- 不读任何fvecs、query向量、qrels或query文本；不训练/调ANN、不接PG。准备仅输出shape、绑定、目录case、4维护、统计及hash。
- 原路径必须在核心合法域，且可用TSV无歧义承载（无空白或NUL），否则失败；保留而不改写原数据。保留空目录语义。
- 查询从深度0/1/2/4/9/16/24/31的存在层，各按(递归条目数、直接孩子数、UTF-8路径)排序等间隔取≤4目录；不存在层注明不适用。另加最大fanout目录、UTF-8首尾末端，去重后≤32anchor，两模式≤64case。
- 专用维护父目录/__scale_prep__/须初始不存在，明确人为新增。sourceLarge按合法非根目录的(后代目录量降序、条目量降序、UTF-8路径)选择，且存在与之互不包含的真实目标；target为这些目标的UTF-8最后项。sourceDeep为与sourceLarge互不包含、非target祖先的最深末端，并列UTF-8序。
- 固定连续MOVE large到专用父、MERGE移动后large到target、MOVE deep到专用父、MERGE移动后deep到target。源/目标和每步几何先由独立判定检查，不根据时延换样；失败保留。

## 实现边界

- code/scale_directory独立目录和构建tag；直接链接原directory_core和原tests/oracle.cpp，不改这些文件、第三方或旧驱动。
- 新原生驱动由旧wiki_experiment/directory.cpp严格限定替换生成：输入shape(N,total_rows)检查、global ID递增/范围检查、专用父目录名称、setup/pass/total资源预算计时。保留原API计时与完整集合/树/catalog/bitmap检查。10000次空时钟校准不替换；不加入Local捷径。
- Python纯目录验证不导入NumPy、不读取向量、不调用生产路径helper；从路径独立重建树、逐条目枚举完整候选、变更完整状态，核对C++完整集合判定输出、查询摘要/全部格位和空间状态。查询选择所需计数用父路径截断累计，避免旧O(D×N)扫描；生产算法不变。
- 负向合同至少覆盖非法shape、shape与实际行数不符、global ID重复/逆序/越界、非法查询模式；必须因预期原因拒绝，不能把任意启动失败当测试通过。

## 运行、门禁与留证

- 新软件build/负向合同在单进程受控范围；四个数据准入worker（每数据集5k ASan、25k Release）串行，每worker三策略/0预热/1pass。同一个5k fixture也做Release单pass，用于新驱动跨构建一致性核验；这只是必要门禁，不是重复旧实验。每个数据大小输出目录独立，拒绝覆盖。
- 每次重型命令启动前连续20秒available≥4GiB并检查D自由≥10GiB；运行≤250ms采样，private≤2GiB、available≥2GiB、命令≤600s、输出≤1GiB。资源/超时拒绝即停，保留现场，不自动关闭应用或放宽预算。编译/短负向合同也受相同运行停止条件，首次采样后各启动再即时检查。
- 采样不是OS内存配额/精确峰值；正式进入条件用建议1.5GiB private准入阈值和1800s单元预算、1440s含裕量筛查。
- 留真实命令、环境、源/二进制/协议/fixture哈希、编译flags、每250ms遥测、stdout与失败状态。归档源码，旧46源码及旧scale评估引用输入保持。无Git提交/推送/重置/清理。

## 完成判定

只有两数据集5k Release/ASan及25k Release均通过、独立核验/跨构建/负向合同/原文件hash通过才关闭软件准入。资源不达标则保留“实现/静态审查完成，运行准入待执行”，不写成完成。

预算将从原生命令setup、包含校验/析构的pass与真实process wall、独立核验器时长/资源重新估算。按单worker setup+23×本次一轮三策略pass+保留退出/监控残差，再乘5，加独立核验器的明确保守场景，报告1.5×筛查与≤1440s及600s门槛；单pass不能证明长期峰值/完整矩阵一定可跑。预计正式格位只用于预算，不伪造正式结果。25k数据本轮只准入，不运行正式。
