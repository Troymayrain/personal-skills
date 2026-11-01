# 在线订阅

仅在用户要求托管或更新订阅时使用。先定位账号、现有项目、部署方式和可回退的当前版本；链接承载原始代理凭据。普通筛选、生成本地文件或导入本地配置，不授权公开发布、覆盖现有服务、变更账户权限或创建付费资源。

FlClash 可通过 URL 获取原生 YAML；优先验证下载内容与要交付的配置一致，再由应用导入并同步。订阅更新是从服务器拉取内容；本地文件变动不会自动改变服务器内容。更新已托管订阅前，先确定实际来源和用户允许的更新范围。

使用 Cloudflare 时，按当时官方文档核实部署路径。独立 Pages Direct Upload 可使用根目录 `_worker.js` 处理请求；Cloudflare 页面、Worker、KV 和 Secrets 是不同资源。不要在业务目录或可列举的静态资源中放明文凭据。优先使用受控密钥存储与高熵、可轮换的访问凭据；若使用随机路径，明确它是持有者凭据，而不是身份认证。服务器日志或拥有部署权限的人仍可能接触链接或配置。对生产及实际存在的预览部署检查：正确凭据取得预期 YAML，错误路径不可读取，响应禁止缓存；再验证 FlClash 导入和同步。按实际工具的发布及确认规则执行。

外链仅是参考，功能、限制和政策应在操作时核对：[Pages Direct Upload](https://developers.cloudflare.com/pages/get-started/direct-upload/)、[Pages Advanced mode](https://developers.cloudflare.com/pages/functions/advanced-mode/)、[Pages bindings](https://developers.cloudflare.com/pages/functions/bindings/)。
