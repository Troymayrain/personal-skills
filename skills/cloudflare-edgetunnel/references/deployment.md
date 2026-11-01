# 部署操作参考

## 已验证的架构

`用户客户端 → 优选入口 → 用户自己的 Pages edgetunnel → 上游直连/配置的 ProxyIP 或链式代理 → 目标站点`

默认路线为 Pages Direct Upload + KV；不是 WARP，不是 Cloudflare Tunnel，也不是完整系统 VPN。CFData-WEB 是可选的 IP 测试工具，不是服务端部署包。

历史案例在 2026-09-09 完成 Pages、KV、ADMIN secret 和外部 DNS 子域名绑定；当时完成登录与 TLS 验证，完整代理验收是后续独立工作。不要把“面板 HTTP 200”当作代理验收。

## 获取源码和准备发布

来源：[cmliu/edgetunnel](https://github.com/cmliu/edgetunnel)。每次部署获取当前 README 和选定 revision 的源文件，固定 commit/tag 并记录 SHA256。历史成功 commit `448a83ced00a43c1d892d5ecbed86a26ea9eeaff` 仅作溯源，不自动锁死为今天应部署的版本。

检查归档，确认部署输出根目录包含 `_worker.js`，而不是多包了一层目录；避免额外上传本地私密文件。Dashboard Direct Upload 支持 `_worker.js`，普通 `functions/` 目录的编译不能照搬此方法。

重点核对本次源代码的变量和认证机制，不能只照抄旧教程：

| 项目 | 应检查的内容 |
|---|---|
| `ADMIN` | Production secret；本用户独立设置，不是 Cloudflare 登录密码 |
| `KV` | binding 名精确匹配源码；namespace 显示名可以不同 |
| UUID/KEY | 旧版本会从 ADMIN/KEY 派生 UUID，也支持显式 UUID；本次必须重新核对 |
| 面板 | 历史版本引用 `edt-pages.github.io`；核对当前前端来源 |
| 订阅转换 | 核对 SUBAPI 和实际发送的数据；初次验收优先本地生成配置 |
| 出口 | 核对 fallback ProxyIP/链式代理；运行自己的 Worker 不意味着所有出口也归自己所有 |

不要复制原案例中的账号、域名或凭据。不要从上游自述“安全”推导已审计安全。

## Cloudflare 操作顺序

1. 登录用户指定账号，核对邮箱验证状态。控制台仍显示 Verify your account 时，等待用户完成验证后重新检查；不通过反复创建项目绕过。
2. 核对项目名未占用，创建独立 Pages 项目。已有同名项目先检查归属和内容，不直接覆盖。
3. 使用固定版本的部署包。在当前工具要求的实际发布边界处理确认；确认页面必须明确账号、项目、代码、预期公开入口和相关依赖。不要擅自启用付费服务。
4. 创建独立 KV namespace，绑定到 Production，binding 名为 `KV`。设置 Production `ADMIN` secret。网页需要输入新凭据时交由用户完成；不在聊天中索要密码。
5. 变量和 binding 设置完成后重新部署同一版本，确认运行的 deployment 是配置更新后的版本。Preview 配置不等于 Production 配置。
6. 获取初始 pages.dev 地址。缺少配置的 Worker 可能返回配置错误页；页面有响应只证明路由执行，不算成功。

若使用 Wrangler/API，先验证当前身份、account 和 project，以及命令版本/当前文档。token 只从本地秘密环境提供，禁止在命令输出、请求 URL、脚本正文、日志或仓库中显示。没有可用 API 授权时用浏览器会话，不从浏览器储存中提取登录 token。

## 自定义子域名，保留外部 DNS

1. 确认用户控制该 DNS 区域；建议复用已有子域名，不默认强制注册新域名。
2. 在 Pages 项目内添加 `vpn.example.com`，选择现有外部 DNS 服务商的 CNAME 路径。
3. 在 DNS 服务商添加 `vpn → <PROJECT>.pages.dev`，保留其 NS。若有冲突记录，先展示具体冲突，不能覆盖邮件或无关记录。
4. 用公共 DNS 查询确认目标，等待 Pages Active 和 SSL enabled，再做 HTTPS 证书校验；DNS 传播和签发是两个状态。有超时则保留项目并说明当前阶段，不删除重建。

外部 DNS 子域名可以使用这条路径；根域名/apex 有不同的 Cloudflare zone/NS 要求。先关联 Pages 自定义域再添加 CNAME，只有 CNAME 而没有关联可能得到 522。DNSHE 只是历史案例选用的服务商，不是必需依赖，其免费政策、后缀可用性和续期均需当次核实。

## 逐层验收及回退

- `/login` 返回有效 HTTPS 页面，证书验证通过。
- 未认证 `/admin` 被重定向到登录或拒绝访问，而不是泄露管理内容。
- 用户登录后取得本实例的节点信息；管理员会话不等于代理 UUID。
- 从最终订阅读取真实节点，解析并核对数量、名字、协议、Host/SNI/path；配置语法验证之后再执行代理请求。
- 真实代理请求由已安装核心完成，至少验证一个 HTTPS 目标，记录状态与失败。配置中声明 UDP 不代表 UDP 已实测。
- 域名的默认背景页、首页伪装页和登录 HTTP 200 均不能证明 VLESS WebSocket 隧道可用。
- 已有项目更新前保留 deployment revision、配置和节点列表的私密备份。回退只动本次明确修改的资源，不重置 KV、删除账号或影响已有站点。

## 官方来源（整理时核对：2026-10-28）

- [edgetunnel 项目与部署说明](https://github.com/cmliu/edgetunnel)
- [Pages Direct Upload](https://developers.cloudflare.com/pages/get-started/direct-upload/)
- [Pages advanced mode](https://developers.cloudflare.com/pages/functions/advanced-mode/)
- [KV bindings 与重新部署](https://developers.cloudflare.com/pages/functions/bindings/)
- [外部 DNS 子域名与 CNAME](https://developers.cloudflare.com/pages/configuration/custom-domains/)

执行时刷新相关来源；UI 标签、套餐额度和第三方依赖可能变化。
