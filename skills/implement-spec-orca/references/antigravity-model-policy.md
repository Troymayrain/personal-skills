# Antigravity 固定模型配置

所有 Antigravity 前端/UI 工作统一使用 **Gemini 4 Hydrogen XHigh**，包括实现、联调、冲突修复和审查修复。
固定参数为 `--model gemini-4-hydrogen-xhigh --effort xhigh`。
独立的 Claude Code 协调者、merger、reviewer 与 Codex 沿用各自配置。

## 1. 一次确认启动能力

首次派工时在实际执行主机确认 `agy` 可用，并通过本机帮助与 `agy models` 确认上述参数。
同一运行复用已确认的结果；环境变化或出现启动异常时才重新检查。
不做额度预检、额度轮询或多模型选择，也不为探测额度额外启动模型会话。

按当前 Orca `orchestration` / `orca-cli` 指南解析 CLI 入口和工作区选择器。
下文 `orca` 代表该入口，占位符使用实际回执或已有工单记录中的值。
参数不兼容或模型不可用时报告具体阻塞，保持指定的模型与强度，不静默改为其他配置。

## 2. 在工单工作区启动新会话

默认在该工单准确的已有 worktree 内创建专用 AGY CLI 终端：

```bash
orca terminal create --worktree "<准确工作区选择器>" \
  --title "agy-<工单>-<阶段>" \
  --command "agy --model gemini-4-hydrogen-xhigh --effort xhigh" --json
```

每张工单、每个实现阶段使用新会话，保留当前信任与权限设置。
从回执记录本轮创建的 terminal handle 及其 `worktreeId`、`ptyId`、`incarnationId`。

利用启动回执和当前会话状态，轻量核对工作区、`antigravity` 身份、就绪状态与实际模型/effort。
缺少信息时才按当前指南补充 `terminal show`、`terminal wait` 或 `terminal read --screen`；
确认后立即派工，不重复探测。启动命令回显和模型自述不能作为实际生效证据。

核验通过后将新会话接管为该阶段的 worker：

```bash
orca orchestration worker-start --task "<阶段 task_id>" \
  --worktree "<同一准确工作区选择器>" --terminal "<新 handle>" --json
```

接管时不同时传 `--agent`、`--model`、`--effort`；提供主技能要求的 spec、工单、范围和验收条件。
Claude 主协调者仍可使用 Chat UI。

若当前 Orca 已支持并能核验原生模型覆盖，也可直接使用
`worker-start --agent antigravity --model gemini-4-hydrogen-xhigh --effort xhigh`，
并传入同一阶段与准确工作区；同一运行复用已确认的启动路径。
若 Orca 拒绝 `xhigh`，使用上述专用 CLI 路径。省略 effort 可能继承其他强度。
两种 `worker-start` 路径都按主技能的 `run.md` 规则登记实际 worktree 路径与分支；终端释放后仍需核销工作区与分支清理单元。

## 3. 阻塞与恢复

- 明确额度不足时，保留当前 worktree、分支及全部已提交和未提交改动，报告受影响前端工作的阻塞。
  停止向已确认额度不足的账号继续派发 Antigravity 任务，不自动更换模型或循环新建 worker。
- 临时网络、速率或服务错误按 Orca 指南有限重试；模型、强度、登录或权限异常按具体原因处理。
- 恢复工作始终使用同一固定模型，在原 worktree 接续剩余事项；先确认旧执行者停写，再按指南恢复同一阶段 Task。
  保留必要的交接与验证记录，遵守 Orca 重试限制，不重跑已完成的后端阶段。
- 独立后端工作和已就绪的整票合并可继续；仍有必需前端工作未完成时，保持相关工单未完成。

## 4. 终端清理

阶段结束或中断交接时，按 Orca 指南停止、释放 worker，并确认执行进程已停写。
接管的专用终端可能记为 `external`；`worker-stop` / `worker-release` 本身不保证关闭它。
仅对本轮创建且身份仍匹配的终端执行 `orca terminal close --terminal "<准确 handle>" --json`，
检查 `ptyKilled` 或明确退出证据；仅有 `retained` 或关闭请求不足以证明停写。
身份不符或仍有写入进程时保留阻塞；下一位写入者须等停写确认后启动。保留用户已有终端和未交付改动。

## 维护依据

- [Google 模型与 Hydrogen XHigh](https://antigravity.google/docs/models/)、[effort](https://antigravity.google/docs/cli/commands/effort/)。
- [Orca orchestration](https://github.com/stablyai/orca/blob/main/skill-guides/orchestration.md)。

运行时以本机版本匹配的命令指南与实际会话状态为准。
