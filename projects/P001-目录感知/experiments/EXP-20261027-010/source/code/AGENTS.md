# 核心代码约定

- 原文方法对应关系和变更边界见 `../notes/core-review.md`、`../notes/operation-spec.md`。
- 不改动 `third_party/croaring` 上游内容；依赖版本/哈希在 LOCK.json。
- 三方案范围查询不得从公共 catalog 或测试判定器取捷径；PE-OFFLINE/TrieHI 非递归保持子集合差。
- 验证保持独立判定器、显式 require（Release 也执行）、固定种子和日志。测试通过不等于论文性能实验成功。
- 用已安装工具的 scripts/build-test.cmd 构建；变更算法后重跑必要正确性检查。大规模实验仍受项目 TASK 限制。
