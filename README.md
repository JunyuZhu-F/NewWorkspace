# Research-Workspace

面向计算机科研论文阅读、实现、实验复现和研究记录的工作区。

## 目录
- `projects/`：论文项目。
- `_templates/`：新项目模板。
- `shared-notes/`：带来源的跨项目技术经验。
- `archive/`：确认后归档的项目。

## 项目文档
每个项目按实际需要维护 `TASK.md`、`REPRODUCTION_PLAN.md`、`STATE.md`、`EXPERIMENTS.md`、`AGENTS.md` 和 `README.md`。根目录 `AGENTS.md` 规定全局科研、安全、验证和读取规则；项目自己的 `REPRODUCTION_PLAN.md` 根据具体论文定制。

## 新建项目
1. 复制 `_templates/P001-papername/` 到 `projects/<项目目录>/`。
2. 根据论文原文、补充材料、官方实现和实际目标填写 `TASK.md`。
3. 核实论文特有路线并制定 `REPRODUCTION_PLAN.md`，不要机械套用固定阶段。
4. 初始化 `STATE.md`，明确哪些内容尚未验证。
5. 只在需要时读取完整计划、历史笔记和实验日志，避免递归读取所有文件。
