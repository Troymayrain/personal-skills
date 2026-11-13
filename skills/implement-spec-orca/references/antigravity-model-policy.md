# Antigravity 模型与额度策略

本文件是所有 Antigravity 前端/UI 阶段的统一规则，包括工单实现、联调、冲突修复和审查修复。
它控制 Antigravity 内部使用的模型，不改变独立 Claude Code 协调者、merger、reviewer 或 Codex 的模型配置。

## 1. 固定优先级

| 档位 | 目标模型与强度 | `agy models` 完整模型 ID | effort 值 |
| --- | --- | --- | --- |
| 1 | Claude Opus 5.5 High | `claude-opus-5-5-high` | `high` |
| 2 | Gemini 4 Argon High | `gemini-4-argon-high` | `high` |
| 3 | Gemini 4 Hydrogen XHigh | `gemini-4-hydrogen-xhigh` | `xhigh` |

完整 ID 已包含强度；显式传入的 `--effort` 必须与该 ID 一致，用于避免继承其他默认强度。
以实际执行主机的官方 `agy models`、帮助和只读查询验证这三组值；ID 变动时核对官方对应关系，
不能凭名称相似选其他模型，或将 `xhigh` 改为 `high`。

按用户说明，这三类模型使用独立额度。运行时记录实际账号与额度桶映射，不因同属 Gemini 就合并额度。
只因明确的模型用量额度不足向后切换，不按任务难度、质量评价或测试成败选档，也不增加第四个候选。
不通过修改全局模型设置、切换账号、开启额外 AI credits 或改变权限策略实现降级。

## 2. 首次派工前的能力检查

1. 在真正执行 worker 的主机上确认官方 `agy` 的版本、路径和登录上下文，读取 `agy --help` 与 `agy models`。
   支持时使用 `agy models --output-format json`。三个 ID 和对应强度都要确认；模型缺失属于配置/可用性问题。
2. 使用当前 Orca 的 `orchestration`、`orca-cli` 指南解析 CLI 入口和工作区选择器。
   下文的 `orca` 代表这个已解析入口，所有占位符须替换为真实回执或既有记录中的值。
3. 只有已确认本机支持只读 print slash command，且没有启用 `disableSlashCommands` 时，才执行：

   ```bash
   agy -p "/usage" --output-format json --print-timeout 20s
   ```

   官方 CLI 从 1.1.11 起支持只读 print `/usage`；更旧或行为未确认的版本改读真实 UI/状态，不把命令当普通 prompt 发送。
   可用相同方式带本档 `--model`、`--effort` 查询 `/model`、`/effort`，验证参数组合；这不替代对实际 worker 会话的核验。
4. `/usage` 的解析以实际版本的返回结构为准。当前 Orca 识别 `status: SUCCESS`、`command.name: usage`、
   `command.data.groups[].buckets[]`，桶含 `id`、`remaining_fraction`、`reset_time`、`disabled`。
   当前 Orca 将 `disabled: true` 的桶排除出计量；不能据此判耗尽，也不能推断整个模型无限可用。
   缺失、未知或解析失败记为 unknown，不解释成零。
   如果输出显示 `num_turns > 0` 或非空 `conversation_id`，停止后续这种探测，报告它实际启动了模型回合。
5. 将模型与实际用量额度桶、账号/执行主机范围对应，保存各生效窗口的剩余量和重置时间。
   只有映射明确时，才据读数跳过已无可用额度的档位；否则从最高的未证实额度不足档位开始，等待明确结果。
   本机 `agy` 的读数不能证明另一个托管 ACP 账号的额度；不同账号范围的状态分开记录。

完成条件：三档参数、运行主机/账号范围和可用启动路径明确。查询不出额度本身不等于额度已用尽。

## 3. 启动并核验真实模型

### 默认路径：专用 AGY CLI 会话，再由 Orca 接管

本策略使用用户本机 `agy` 的模型与额度，因此默认让三个档位都走同一条显式 CLI 路径。
Claude 主协调者仍可使用 Chat UI；这里只为 Antigravity worker 创建专用终端。
这也处理部分 Orca 版本不接受 `--effort xhigh`、或省略 effort 后继承了其他强度的问题。

1. 读取最新共享档位。在已经创建并核验的**原工单 worktree** 内新建专用 terminal。
   以下示例为第一档；第二、三档仅按表替换模型 ID 和 effort：

   ```bash
   orca terminal create --worktree "<准确工作区选择器>" \
     --title "agy-<工单>-<阶段>-<attempt>" \
     --command "agy --model claude-opus-5-5-high --effort high" --json
   ```

   这是全新会话，不附加 `--continue`、`--resume` 或 `-p` 业务提示词。
   保留当前信任与权限设置；登录、信任提示、更新提示和启动超时按实际原因处理。
2. 从回执取得准确 handle，保存“本轮创建”标记及 terminal 的 `worktreeId`、`ptyId`、`incarnationId`。
   使用当前指南支持的命令核验：

   ```bash
   orca terminal show --terminal "<新 handle>" --json
   orca terminal wait --terminal "<新 handle>" --for tui-idle --timeout-ms 30000 --json
   orca terminal read --terminal "<新 handle>" --screen --json
   ```

   要求实际 worktree 正确、`agentIdentity` 为 `antigravity`、AGY 已就绪，且当前客户端状态显示目标模型与强度。
   若当前画面不足以确认，使用本机官方支持的会话只读查看方式；不能用启动命令的回显、旧 scrollback 或模型自述自证。
   未确认时不派业务写入；清楚报告具体缺项。
3. 核验后，把这个新会话绑定到既有阶段 Task，并提供主流程要求的上下文与交接记录：

   ```bash
   orca orchestration worker-start --task "<阶段 task_id>" \
     --worktree "<同一准确工作区选择器>" --terminal "<新 handle>" --json
   ```

   接管模式不再传 `--agent`、`--model` 或 `--effort`；真正的执行者已由 AGY 进程身份核验。
   这里使用的是本轮刚创建的新 terminal，不复用上一阶段或用户已有会话。

### 可选路径：原生 worker 模型覆盖

只有当前安装版本能准确表达所选模型/强度、实际 provider 状态可核验，且账号范围与额度记录一致时，
才可采用 `worker-start --agent antigravity --model <完整ID> --effort <level>`，沿用用户的 Chat/CLI 设置。
若本机仍不接受 `xhigh`，使用上述专用 CLI 路径；参数拒绝是兼容问题，不推进额度档位。
仅省略 `--effort` 不保证消除保存的 effort，`launch.effective` 也不能替代 provider 回读。
用户明确要求 Antigravity 只能用 Chat 时，若无法满足精确模型/强度，报告兼容阻塞，不擅自改低强度。

完成条件：实际 provider 模型/强度与表中本档相符、账号范围正确、阶段 Dispatch 和工作区绑定可核对。
后续输出若表明模型被自动换成了其他型号，按配置异常暂停该阶段，不把它当作已按本策略完成。

## 4. 同一 run 共用额度状态

由 Claude 协调者在可恢复的运行记录中单点维护以下信息；这些是记录字段，不是新增 Orca API：

- `run_id`、执行主机/账号范围、三档映射、`active_tier`、`quota_blocked_tiers`、状态修订号；
- 每个额度阻塞档位的实际 provider 证据、额度桶、观察时间及可确认的重置时间；
- 每次 attempt 的业务工单、阶段 Task、Dispatch、模型/effort、worktree、分支、HEAD、终端身份及停写证据。

所有并行前端 worker 共用其账号范围的状态，worker 只报告证据，不各自递增全局档位。
确认额度不足后，先把**失败 attempt 实际使用的档位**加入集合，再选顺序中第一个未被额度阻塞的档位。
同一档的重复/迟到错误只登记一次；不能执行简单的 `active_tier++`。
旧 run 的事件不修改新 run；正常的旧档在途 worker 可以完成，不因同伴降档而重跑。

每次真正启动前再读共享状态。若其他票已使档位继续下降，直接用最新可用档位，不重试已确认不足的中间档。
同一 run 更换工单、阶段、worker、进入最终修复或从中断恢复，都保留这份状态。

## 5. 只有明确用量额度不足才降级

读取 `worker-show`、`worker-read --source auto` 及实际 provider 错误；CLI 必要时读取准确 terminal 的当前屏幕。
若有 `AGY_ERROR` 结构化错误，按本机真实字段解析并保存必要证据。不要要求交互 TUI 一定输出 headless 的错误格式。

| 证据 | 动作 |
| --- | --- |
| 明确对应当前模型/额度桶的用量额度不足或耗尽；或映射明确的有效用量窗口剩余为零 | 更新额度状态，按下一节恢复 |
| 仅 `429`、`RESOURCE_EXHAUSTED`、退出码 3、failed、idle 或超时，没有明确原因 | 继续诊断；不登记额度耗尽 |
| 每分钟速率/并发限制、短暂过载、网络错误或 5xx | 按当前指南和服务退避信息有限重试，仍失败则报告阻塞 |
| 未知模型、无效 effort、实际模型不符、登录/权限失败 | 配置或访问问题；修正或报告，不降档 |
| 测试失败、审查问题、上下文限制、工具错误 | 处理相应工作或执行问题，不降档 |
| 全账号余额、账单或额外 AI credits 问题，无法归属某个模型池 | 单独报告；不把三个模型池猜成已耗尽 |

`quota_blocked` 表示当前请求因用量额度不可用，不能据此捏造剩余 token 为精确的零。
记录所有相关用量窗口；一个窗口到重置时间，不证明其他限制也已解除。

## 6. 降档时接续当前阶段

1. 根据真实错误更新共享状态，停止向已确认额度不足的档位派新任务。
   记录失败 attempt 和当前进度；前端中断不撤销已经完成的后端阶段。
2. 先按指南对旧 Dispatch 执行 `worker-stop`，再确认它及可能写入该工作区的执行进程已经停写：
   - Orca 受管会话核对退出证据；仅发出关闭动作或 `stop_unknown` 不够。
   - 默认路径中的专用 terminal 被接管后，在 Orca 资源账本中可能属于 `external`；
     `worker-stop`/`worker-release` 不保证关闭它。仅对本轮创建且身份仍匹配的准确 terminal，
     使用 `orca terminal close --terminal "<准确 handle>" --json`，检查 `ptyKilled` 或后续明确退出证据。
   - 若身份已变化、仍有写入进程或无法证明停写，阻塞该票；不得启动第二个写入者。
3. 保留原 worktree、branch、已提交、暂存、未暂存及未跟踪文件。
   保存当前 HEAD、改动范围、已完成/剩余事项、测试结果和异常；未执行的测试明确记为未验证。
   不因切模型 reset、clean、重建工作区或把阶段标为完成。
4. 按当前 Orca 回执/恢复指南结算旧 Dispatch 并确认可重试。以同一阶段 Task、新 attempt、新 AGY 会话接续，
   使用相同准确 worktree；适用时带 `--retry-of <旧 dispatch_id>`，显式重给 placement。
   不通过新建 Task/Run 避开重试熔断；达到平台限制时按真实阻塞报告。
5. 新 worker 先核对交接记录和现有改动，再完成剩余工作与必要回归。整票通过验证并实际合入 integration 后，
   才能解锁下游；额度降级本身不释放任何业务依赖。

正常阶段结束也要记录并清理本轮专用终端；不能把 external 的 `retained` 当作已关闭。
清理保留准确身份检查，只处理本轮创建的资源，不关闭用户原有终端，不使用批量 `--all`。

## 7. 末档不足与下一轮

第三档也有明确额度不足证据，且此前档位均已被本轮状态排除时，停止新的 Antigravity 派工与自动重试。
保留受影响阶段进度、未合入分支、审查 findings 和已知重置时间，报告前端额度阻塞。
依赖已满足的独立后端工作与可完成的整票合并可以继续；有必需前端工作未完成时不报告整项完成或将 PR 标记 ready。
若前端工作实际上都已完成，单纯没有余量不阻止既定的最终审查和正常收尾。

同一 run 默认只降不升，不在每张新票重新试第一档，也不后台轮询等待重置。
用户要求重新评估额度或明确启动新 run 时，刷新实际读数并从最高可用档重新选择；
不能把旧状态直接当作永久耗尽，也不能在额度尚未恢复时因新 run 就假定可用。原工单进度照常保留。

## 维护依据与版本边界

运行时以本机帮助、官方指南和实际 provider 状态为准。以下为编写时核查的来源，不代表已在用户机器运行验证：

- [Google 模型与 Hydrogen XHigh](https://antigravity.google/docs/models/)、[effort](https://antigravity.google/docs/cli/commands/effort/)、[/usage](https://antigravity.google/docs/cli/commands/usage/)、[CLI changelog](https://github.com/google-antigravity/antigravity-cli/blob/main/CHANGELOG.md)。
- [Orca worker-start 参数](https://github.com/stablyai/orca/blob/6734880408c22db28807e6ec99494d8f2f909beb/src/cli/specs/orchestration-worker-specs.ts)。
- [2026-11-13 核查的 Antigravity effort 枚举](https://github.com/stablyai/orca/blob/6734880408c22db28807e6ec99494d8f2f909beb/src/shared/agent-session/options/agent-session-option-catalog-antigravity.ts)：当时尚未包含 `xhigh`，不能据此假定所有后续版本也受限。
- [原样终端命令启动](https://github.com/stablyai/orca/blob/6734880408c22db28807e6ec99494d8f2f909beb/src/main/runtime/terminal/launch/runtime-agent-terminal-startup.ts)、[接管身份与工作区校验](https://github.com/stablyai/orca/blob/6734880408c22db28807e6ec99494d8f2f909beb/src/main/runtime/rpc/methods/orchestration/worker/start/placement/explicit-worker-terminal-validation.ts)。
- [停止与恢复](https://github.com/stablyai/orca/blob/6734880408c22db28807e6ec99494d8f2f909beb/skill-guides/orchestration/references/recovery-and-cleanup.md)、[Orca 的 AGY usage 解析](https://github.com/stablyai/orca/blob/6734880408c22db28807e6ec99494d8f2f909beb/src/main/rate-limits/providers/antigravity/antigravity-usage-response.ts)。
