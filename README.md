# Personal Skills

个人使用的可复用 Agent Skills。每个技能放在 `skills/<技能名>/`，并包含自己的 `SKILL.md` 和所需资源。

## 技能

- `cloudflare-edgetunnel`：部署或维护 Cloudflare EdgeTunnel，并按当前网络实测筛选代理节点。

## 安装

先在目标电脑配置能访问此私有仓库的 GitHub 凭据。然后列出技能：

```bash
npx skills add Troymayrain/personal-skills --list
```

安装 EdgeTunnel 技能到 Codex 的用户目录：

```bash
npx skills add Troymayrain/personal-skills --skill cloudflare-edgetunnel --agent codex --global
```

订阅链接、账号凭据、实例配置和测速数据不存入此仓库。技能使用实际环境的配置，并在缺少必要信息时引导用户提供。
