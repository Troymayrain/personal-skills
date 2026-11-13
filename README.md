# Personal Skills

个人使用的可复用 Agent Skills。每个技能放在 `skills/<技能名>/`，并包含自己的 `SKILL.md` 和所需资源。

## 技能

- `cloudflare-edgetunnel`：部署或维护 Cloudflare EdgeTunnel，并按当前网络实测筛选代理节点。
- `implement-spec-orca`：接收 spec 链接或路径，沿用 mattpocock 的 `implement-spec`，通过 Orca 编排 Claude 统筹与审查、Codex 后端和 Antigravity 前端。

## 安装

先在目标电脑安装 Node.js 和 npm。然后列出技能：

```bash
npx skills add Troymayrain/personal-skills --list
```

安装 EdgeTunnel 技能到 Codex 的用户目录：

```bash
npx skills add Troymayrain/personal-skills --skill cloudflare-edgetunnel --agent codex --global
```

安装 Orca 编排技能到 Claude Code 的用户目录：

```bash
npx skills add Troymayrain/personal-skills --skill implement-spec-orca --agent claude-code --global
```

在 Orca 的 Claude Code 主协调会话中调用：

```text
/implement-spec-orca [Spec 的链接或路径]
```

运行前需具备 mattpocock 的 `implement-spec`、`tdd`、`code-review`，以及可用的 Orca、Claude Code、Codex 和 Antigravity。

Antigravity 前端阶段默认按 **Claude Opus 5.5 High → Gemini 4 Argon High → Gemini 4 Hydrogen XHigh** 使用模型。
只有明确的模型额度不足才切换；同一 run 共用降级状态，保留原工单工作区与进度。
默认通过 Orca 创建带显式模型参数的专用 `agy` CLI 会话，再接管为 worker，以覆盖本机默认模型并兼容 `xhigh`。
Claude 主协调者仍可使用 Chat UI。具体的参数核验、额度判断与恢复规则见
[Antigravity 模型策略](skills/implement-spec-orca/references/antigravity-model-policy.md)。

订阅链接、账号凭据、实例配置和测速数据不存入此仓库。技能使用实际环境的配置，并在缺少必要信息时引导用户提供。
