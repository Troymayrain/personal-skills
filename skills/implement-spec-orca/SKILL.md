---
name: implement-spec-orca
description: >-
  在用户明确要求执行已有 spec 时使用：接收 spec 链接或路径，沿用 mattpocock/skills
  的 implement-spec 流程，通过 Orca 让 Claude 统筹、合并和审查，Codex 实现后端，
  Antigravity 使用 Gemini 4 Hydrogen XHigh 实现前端/UI。适用于包含前端、后端和全栈工单的依赖图。
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
   将它作为主流程依据；本技能明确覆盖的角色、交接、修复、运行记录和清理规则优先，其余步骤沿用该版本。
   读取其定义不依赖它是否允许模型自动调用；不要改写原技能来启用调用。
2. 在能访问目标项目的 Orca Claude Code 主协调会话中执行。确认项目、tracker 配置和 spec 对应关系。
   若缺少 `implement-spec`、tracker 配置或可用的 Orca 执行环境，说明具体缺项并停止派工。
   用户只要求计划或预演时，可给出计划，保持未执行状态。
3. 读取已安装的 Orca `orchestration` 技能，按其规则解析当前会话的 CLI 入口，
   再运行该入口的 `skills get orchestration --full`；需要工作区操作时加载 `orca-cli` 指南。
   使用当前安装版本支持的命令，依照失败回执恢复。主协调者可使用 Chat UI 或 TUI；
   Antigravity 按下述固定模型配置启动。
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

### run.md 运行台账

创建本轮分支/worktree 或启动任何 worker 前，确定本轮唯一的 `run.md`。
使用项目约定的持久运行目录；没有约定时，放在
`<git-common-dir>/orca-runs/<run_id>/run.md`（用 `git rev-parse --git-common-dir` 解析并转为绝对路径）。
台账由协调者维护，放在待清理 worktree 之外，保留到最终报告之后。

先记录 `git worktree list --porcelain` 和 `git branch` 的初始清单，标明用户已有、主工作区和应保留分支。
**每次 `worker-start` 都追加派工记录**，覆盖 Codex、Antigravity 两种启动路径、Claude merger/reviewer 及重试：
启动前写入已知目标；收到回执后用实际 Git 状态核验并补全，不以预计名称代替真实路径/分支。
启动失败也记录结果及已经创建的资源。每条记录包含：

- 工单/阶段、角色、Task/Dispatch、启动结果；
- worktree 绝对路径、实际本地分支名、HEAD，以及本轮创建还是借用；
- 对应远端和分支引用（没有则记无），合入目标及确认合入的提交；
- 清理单元标识、worktree 状态、本地分支状态、远端分支状态及证据/保留原因。

同一 `worktree + 分支` 的多阶段、重试记录关联同一个清理单元，保留派工历史，清理时只处理一次。
detached HEAD 明确记录为“无分支”及其 SHA，不推测分支名；分支切换、改名或工作区移动时及时更新对应关系。
清理必须按台账逐项核销；记录与现场不符时先查明并补齐，不凭记忆选取删除对象。

### Antigravity 固定模型

所有前端工单、全栈工单的前端阶段、联调、冲突修复和最终审查中的前端修复，
统一使用 Gemini 4 Hydrogen XHigh。
首次派工前读取 [Antigravity 固定模型配置](references/antigravity-model-policy.md)，
按其中的明确参数启动并做必要的会话核验；同一运行复用已确认的启动路径。
模型选择固定，不执行额度预检、档位管理或自动切换。

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

Antigravity 派工注明固定模型与 effort；恢复任务同时提供现有进度和交接位置。
要求 worker 在实现前核对实际工作区与基础提交，并读取所需资料。
资料不可读或基准不符时，先向协调者报告并解决，再继续实现。

将工单与阶段 Task、Dispatch、工作区、提交和合并结果对应写入本轮 `run.md`；其他笔记引用这份台账。
阶段 `worker_done` 只表示该阶段结束，不能提前把整张工单或其依赖判为完成。
Antigravity 启动或执行受阻时按固定模型配置处理，保留原工单进度。

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

### 按清理单元逐项核销

把 **worktree 与它的本地分支** 作为一个清理单元，按 `run.md` 逐项处理，不以移除目录代替分支清理。

1. 按 Orca 指南释放本轮 worker，并按固定模型配置关闭本轮创建的专用 Antigravity terminal，确认所有相关执行者停写。
   核对台账、实际路径、分支 tip、合入记录和工作区状态；仅清理本轮创建、成果已合入且无未交付改动的单元。
   保留用户已有资源、主工作区和仍需交付的工作。integration PR 尚未合并时，保留其工作区、本地与远端分支。
2. **先找项目文档中的清理工具**：检查 `AGENTS.md`、`CLAUDE.md`、README 及其指向的开发文档。
   找到时读清工具说明与实现，先按文档运行预览；逐项核对待删路径、分支、合入目标和远端操作均在本轮可清理范围内，
   再执行同一范围的 `--apply`；对象或 tip 变化时重新预览。
   预览范围过大、无法限定目标或使用强删时停止并记录阻塞，不直接执行。
   所有路径（包括工具内部）均不得使用 `git branch -D` 或等价的强制删除。
3. **找不到项目清理工具时，用 Git 安全删除**。明确将继续保留的合入目标：工单/修复分支通常是 integration；
   integration 自身仅在 PR 已合并、最终目标已核实后再考虑清理。在保留的目标工作区核验两端 tip：

   ```bash
   git -C "<保留目标工作区>" merge-base --is-ancestor "<待清理分支-tip>" "<保留目标-tip>"
   ```

   仅退出码为 0 才继续；非祖先（包括 squash/rebase 后无法证明）或检查出错时保留并报告。
   再核对现场未变化、工作区干净且分支未被其他 worktree 使用，依次执行：

   ```bash
   git -C "<保留目标工作区>" worktree remove -- "<台账中的 worktree 绝对路径>"
   git -C "<保留目标工作区>" branch -d -- "<台账中的本地分支名>"
   ```

   detached worktree 用登记的 HEAD 验证合入，仅移除 worktree，本地分支记为“不适用”。
   使用保留目标分支所在的工作区执行 `branch -d`；Git 仍可能按 upstream 检查合入状态。
   若 `-d` 拒绝，保留分支并记录原因，不改 upstream、强删或绕过检查；移除 worktree 不加 `--force`。
4. 每项操作后回读实际状态，分别更新台账中的 worktree 和分支结果。
   已移除 worktree 但分支仍在时记“部分清理”。工具成功执行后未覆盖的登记分支，沿用第 3 步的目标核验、祖先检查和 `branch -d`；
   因越界或强删被阻塞的工具路径仍保持阻塞。只有 worktree 与本地分支都确认移除（无分支时记不适用）才核销完成。
   已不存在的资源按实际证据核销，预期保留项写明原因；保留运行台账本身。
5. 单独核对台账对应的**服务器远端分支**，可用
   `git ls-remote --heads "<remote>" "refs/heads/<branch>"`；本地 `git branch -r` 的缓存不能证明远端现状。
   远端删除按原流程与项目约定的授权范围执行，不能因本地清理成功而默认删除；未推送、仍存在、已删除或未确认分别记录。
   网络或权限失败记“未确认”，不声称远端已清理。

### 完成标准与最终报告

清理完成标准增加：**实际运行 `git worktree list` 和 `git branch`，结果与 `run.md` 中已明确的预期保留清单一致，只剩预期项且没有缺项。**
预期项以运行前保留清单、当前 PR/交付状态为依据；不能把漏删或失败项事后改成预期项来通过验收。
所有本轮应清理单元均须完成核销；存在额外项、缺项、部分清理或未解决阻塞时，报告清理未完成并列出原因。

最终报告逐工单结果、集成提交、验证与审查证据、PR/工单状态、`run.md` 路径及未解决阻碍。
列明 worktree 清理结果、**本地分支与服务器远端分支各自的状态**（已删除/保留及原因/未确认），
附最终 worktree/本地分支清单及核销结果。包含 Antigravity 实际使用的模型/effort。
分别说明实际执行、未执行、失败或跳过的检查，不把文档检查或计划当作运行成功。

## 维护依据

- 主流程：[mattpocock implement-spec](https://github.com/mattpocock/skills/blob/main/skills/engineering/implement-spec/SKILL.md)
- 编排机制：[Orca orchestration](https://github.com/stablyai/orca/blob/main/skill-guides/orchestration.md)
- 参数机制：[Claude Code skill arguments](https://code.claude.com/docs/en/skills#pass-arguments-to-skills)
- 清理语义：[git worktree](https://git-scm.com/docs/git-worktree)、[git merge-base](https://git-scm.com/docs/git-merge-base)、[git branch](https://git-scm.com/docs/git-branch)

运行时优先读取本机已安装技能和版本匹配的 Orca 指南；上述链接用于核对来源，不替代本机命令契约。
