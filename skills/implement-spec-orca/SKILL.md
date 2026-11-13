---
name: implement-spec-orca
description: >-
  在用户明确要求执行已有 spec 时使用：接收 spec 链接或路径，沿用 mattpocock/skills
  的 implement-spec 流程，通过 Orca 让 Claude 统筹、合并和审查，Codex 实现后端，
  Antigravity 实现前端/UI，并按指定模型优先级处理额度不足。适用于包含前端、后端和全栈工单的依赖图。
---

# Implement Spec with Orca

## 1. 解析输入

本次 spec 引用：$ARGUMENTS

只要求一个 spec 链接或路径，从 spec 读取关联工单。调用示例：

```text
/implement-spec-orca https://github.com/OWNER/REPO/issues/123
/implement-spec-orca docs/specs/profile.md
/implement-spec-orca "/Users/me/My Project/docs/功能 spec.md"
```

保留含空格的路径为一个整体。相对路径以目标项目目录为基准，不以技能目录为基准。
如果调用环境没有展开参数，从用户本次请求读取明确的 spec 引用。参数为空、仍为模板变量、
只有示例占位符，或存在多个无法判定的 spec 时，先只询问缺失或歧义的引用，不创建运行、分支或 worker。

## 2. 加载流程与执行环境

1. 定位并完整读取用户已安装的 mattpocock `implement-spec`，通过准确技能名称或命名空间区分同名技能。
   将它作为主流程依据；本技能明确覆盖的角色、交接和修复规则优先，其余步骤沿用该版本。
   读取其定义不依赖它是否允许模型自动调用；不要改写原技能来启用调用。
2. 在能访问目标项目的 Orca Claude Code 主协调会话中执行。确认项目、tracker 配置和 spec 对应关系。
   若缺少 `implement-spec`、tracker 配置或可用的 Orca 执行环境，说明具体缺项并停止派工。
   用户只要求计划或预演时，可给出计划，保持未执行状态。
3. 读取已安装的 Orca `orchestration` 技能，按其规则解析当前会话的 CLI 入口，
   再运行该入口的 `skills get orchestration --full`；需要工作区操作时加载 `orca-cli` 指南。
   使用当前安装版本支持的命令，依照失败回执恢复。主协调者可使用 Chat UI 或 TUI；
   Antigravity 的启动方式、模型与额度按下述专门策略处理。
4. 核对 `claude`、`codex`、`antigravity` 可用；确认各 worker 可读取 spec、工单、项目规范、
   `tdd` 和必要的共享笔记。支持技能工具时调用，不支持时读取同一技能正文及其必要引用。
   私有链接或本地资料若不能直接共享，由协调者提供对应的可读材料，避免假设子会话继承主会话内容。

完成条件：spec、工单图、运行项目、必需技能和三个实际 agent 均已明确且可访问。
先简要报告工单分类、执行者分配和首批可执行工单，然后开始执行。

## 3. 角色与作用范围

| 角色 | Orca agent ID | 工作范围 |
| --- | --- | --- |
| 主协调者 | `claude` | 依赖、必要契约、派工、阻碍、合并队列与验收 |
| 后端实现 worker | `codex` | 后端、API、数据库、后端测试及明确分配的共享契约代码 |
| 前端实现 worker | `antigravity` | 前端、UI、交互、样式、接口接入与相关验证 |
| merger worker | `claude` | 串行整合一张已完成工单、检查结果并报告 |
| reviewer | `claude` | 全部工单合入后，在新会话中执行 mattpocock 的 `code-review` |

通过 Orca `worker-start` 派发真实的对应 agent。新建会话时按角色显式指定 `--agent`；
Antigravity 也可按模型策略接管本轮新建、已核验身份的专用 `agy` terminal，遵守接管模式的互斥参数规则。
每个新工单、实现阶段、合并任务和正式审查使用新的 worker 会话。
Claude 和 Codex 的模型沿用现有配置，除非用户另行指定；Antigravity 遵循下述策略。
实现 worker 只执行分配范围，不递归运行整个 `implement-spec` 或接管全局工单图。
正式 reviewer 可按 `code-review` 原定义使用 Claude 审查子任务，保留 Standards 与 Spec 两个维度。

从原 spec 和 tickets 发现工作；不要求用户重复填写工单来源，不预设固定并发数量。
在依赖和实际资源允许时尽可能并行，同时保持同一 worktree 一个写入者、integration branch 一个 merger。

### Antigravity 模型与额度

首次派发任何前端/UI 阶段前，完整读取 [Antigravity 模型策略](references/antigravity-model-policy.md)。
其中的优先级、运行前检查、启动与实际生效验证、额度错误分类、共享状态、停写接力和清理规则，
统一适用于前端工单、全栈工单的前端阶段、冲突修复与最终审查中的前端修复。
同一 run 的后续派工和恢复继续使用同一份状态；不会因为换票、换 worker 或进入审查修复就重置。
模型降级只恢复受影响的当前阶段，不改变业务工单身份、依赖、worktree、分支或完成条件。

## 4. 每张工单的实现与交接

保留一个 integration branch，以及每张原业务工单一个独立 worktree 和 branch。
让 Orca 从当前 integration 的已提交版本创建工单工作区，核验实际基准；纠正基准时保留已有改动。

- **仅后端**：交给新的 Codex worker。
- **仅前端/UI**：交给新的 Antigravity worker。
- **全栈**：协调者先明确必要接口与共享类型及其实现负责人；在同一工单 worktree 内接力：
  1. 新 Codex worker 完成后端，提交并报告阶段成果。
  2. 确认它已停止写入后，向新的 Antigravity worker 传入该工单的准确已有工作区选择器及提交。
  3. Antigravity 完成前端与联调，全部阶段及整票验证完成后再进入合并队列。

后续阶段使用该工单的工作区，不把协调者的 `current` 当作它，也不复用上一阶段的 terminal 会话。
每个实现阶段遵循原流程的 `tdd` 和已约定测试边界；需要澄清时通过 Orca 向主协调者提问。
不额外套用带有独立完整审查流程的 `implement`。

每次派工提供简短、自包含的任务说明：

- 可访问的 spec、ticket、规范、共享笔记指针；
- 本阶段目标、可修改范围、验收条件；
- 工作区、分支、基础提交和所需上游产物；
- 交付要求：结果 commit SHA、验证命令与结果、未解决问题。

Antigravity 的任务说明还需携带本次 attempt、模型档位、实际模型/effort、额度状态记录和交接位置。
要求 worker 在实现前核对实际工作区与基础提交，并读取所需资料。
资料不可读或基准不符时，先向协调者报告并解决，再继续实现。

将工单与阶段 Task、Dispatch、工作区、提交和合并结果对应记录在可恢复的运行状态或共享笔记中。
阶段 `worker_done` 只表示该阶段结束，不能提前把整张工单或其依赖判为完成。
遇到 Antigravity 额度、启动或模型不符事件时，先按模型策略处理，再决定该阶段是否可以继续。

## 5. 逐票合并与持续推进

1. 整票交付前，在工单分支合入最新 integration tip，执行必要验证并提交结果。
2. 一张完整工单就绪就进入串行 merger 队列。合入前再次检查 integration tip；
   如果已变化，先在工单分支同步并验证。业务代码冲突按领域回派实现 worker。
3. merger 成功将整票代码合入 integration、相关验证通过后，记录该工单已落地，立即推进可执行工单集合。
   原生任务依赖若需要建立对应节点，下游依赖前置工单的成功合入节点，不依赖某个实现阶段的完成节点。
4. 从本轮已合入记录计算可执行工单；外部 issue 等待最终 PR 合并才能关闭时，不用其 Open 状态阻塞已具备代码基础的下游。
5. 按原技能条件在首次合入后创建 draft PR。创建任务图后，协调者仍负责持续派工。
   启动当前可并行的 workers 后按 Orca 指南结束本轮等待唤醒，处理回报后继续；不另写轮询脚本抢读消息。

完成条件：每张工单都有可核对的整票成果、成功合入记录和验证证据；失败或未合入的工单不释放其业务依赖。

## 6. 最终审查与按领域修复

全部工单合入后，给新的 Claude reviewer 提供原 spec、工单、明确固定的 diff 基准、
当前 integration 提交及验证证据，执行 mattpocock 的 `code-review`，保存两个维度的报告与实际审查提交。
实现阶段按各工单验收条件验证，不反复对尚未完成的整个 spec 发起完整审查。

明确覆盖原技能“由一个 implementer 修复全部审查问题”的规则：

- 仅后端问题：由新的 Codex worker 集中修复。
- 仅前端/UI 问题：由新的 Antigravity worker 集中修复。
- 混合问题：使用同一个修复批次、worktree 和 branch，由新的 Codex 与 Antigravity worker 按领域串行接力。

修复成果沿用 merger 流程合回 integration。Claude 针对已有 findings 和必要回归复核，
未解决项继续定向处理；默认不因每次修复重启整个 spec 的广泛审查。
评审任务完成只表示报告产出；最终验收还要求问题已解决或有明确处置、验证证据覆盖当前候选版本。

## 7. 收尾与报告

按原技能及项目 tracker 约定创建或更新 PR、标记 ready、处理工单和报告 integration branch。
只有成果、验证与审查处理完成才收尾；有阻碍时保持对应工作未完成并说明原因。

按 Orca 指南释放本次运行的 worker；按模型策略分别处理 Orca 受管资源与接管的专用 Antigravity terminal。
再清理本次创建、已确认合入且没有未交付改动的实现 worktree。
释放 worker 不等于删除 worktree；保留用户已有工作区和仍需恢复的资料。

最终报告逐工单结果、集成提交、验证与审查证据、PR/工单状态及未解决阻碍。
包含 Antigravity 各阶段实际使用的模型/effort、切换证据、保留进度和仍受额度阻塞的工作。
分别说明实际执行、未执行、失败或跳过的检查，不把文档检查或计划当作运行成功。

## 维护依据

- 主流程：[mattpocock implement-spec](https://github.com/mattpocock/skills/blob/main/skills/engineering/implement-spec/SKILL.md)
- 编排机制：[Orca orchestration](https://github.com/stablyai/orca/blob/main/skill-guides/orchestration.md)
- 参数机制：[Claude Code skill arguments](https://code.claude.com/docs/en/skills#pass-arguments-to-skills)

运行时优先读取本机已安装技能和版本匹配的 Orca 指南；上述链接用于核对来源，不替代本机命令契约。
