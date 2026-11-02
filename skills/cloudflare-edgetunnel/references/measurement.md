# 物理出口与代理测速

## 物理出口

- 先核对系统代理、活动 TUN、到候选的系统路由和物理网卡。TUN 存在时，`curl --noproxy '*'` 仍可能经过代理；`198.18.0.0/15` Fake-IP 不是远程真实地址。
- 启动独立 Mihomo，监听地址限于 loopback，不启用新 TUN，不改系统代理或用户运行中的配置。选用与客户端兼容的核心；不要假定应用内核可独立运行。
- 在隔离核心中绑定实际物理网卡。核对 `/configs` 和 `/proxies/<group>`；缓存可能恢复旧选择，因此明确将隔离组切为 `DIRECT`，再用隔离核心访问公网出口检测服务。另用明确绑定该物理网卡的独立请求验证相同公网出口，必要时使用经独立 DNS 核验的真实目标 IP。两条结果一致并结合路由与网卡绑定证据判断物理出口；若存在已识别的非直连 TUN 出口，还须确认结果与该出口不同。没有 TUN 或 TUN 为 DIRECT 时，出口可以相同。IP 本身不必写入公开报告。
- macOS 可用 `route -n get <真实IP>`、`scutil --proxy`、`curl --interface <网卡> --resolve <域名>:<端口>:<真实IP>` 和 Mihomo `interface-name`；网卡名和 DNS 结果必须当次发现。其他系统按其平台机制检查；`interface-name` 和绑定语义必须实测，不将 macOS 命令生搬硬套。未经用户授权，不关闭 TUN、不改系统路由或切换用户现有核心。

## 测试口径

候选源可能来自优选清单或第三方反代，例如 [BestCF](https://bestcf.pages.dev/)。实时获取候选并剔除占位行；源列表的测速和带宽只代表其测量条件。按 IP 与端口去重，确认候选能按原配置完成 VLESS/WS/TLS 等真实代理连接。TCP 握手、Cloudflare 网站首页和源列表上的延迟不是代理 URL Test。保持证书校验，候选端口以来源和实测为准。

使用一个测试 URL，例如 `https://www.gstatic.com/generate_204`；记录预期状态、核心版本、`unified-delay`、超时、并发和时间。`unified-delay: true` 下的数值不等于从零建立连接的总耗时。Mihomo delay API 的延迟本身不能证明目标返回预期 HTTP 状态；对最终候选另发 HTTPS 请求，核验状态，例如该 URL 的 204。

随技能附带的 `scripts/measure_mihomo.py` 只读取隔离核心或已授权核心的本地 API，不启动核心、不改变选择。先查看 `--help`。目标 JSON 为节点名数组，或带 `name`、可选 `max_ms` 的对象数组；`max_ms: null` 表示不设门槛。默认按地区设置门槛：日本和新加坡为 100 ms，美国为 200 ms；目标名称必须与实际配置一致，例如：

```json
[
  {"name": "JP-01", "max_ms": 100},
  {"name": "SG-01", "max_ms": 100},
  {"name": "US-01", "max_ms": 200}
]
```

使用经确认的 controller 地址，示例：

```sh
python3 scripts/measure_mihomo.py \
  --controller http://127.0.0.1:18892 \
  --targets targets.json --output measurements.json \
  --url https://www.gstatic.com/generate_204 \
  --samples 10 --timeout-ms 5000 --concurrency 2 \
  --unified-delay true --network-note '物理出口已独立核验'
```

API secret 只从 `MIHOMO_API_SECRET` 环境变量读取。脚本的 `network-note` 只是记录，不能代替实际出口验证。脚本记录原始样本、错误、失败数、最大值、`mean_ms` 和完成轮数；不足全部轮次或任何一次失败时，不把成功样本均值当作完整均值。默认门槛要求 10 次全部成功且每次严格低于对应阈值；用 `strict_pass` 判断，再按 `mean_ms` 排序。等于阈值不合格；平均值合格不等于每次合格。用户另行指定次数或门槛时按其要求执行。限定候选池时报告规模、排除数、时段与方法；不能称作全网最低。

## 地区与可信边界

对每个入选节点分别记录：来源标签；该入口对应的 Cloudflare trace `colo`；经代理访问普通目标时的出口 IP 国家；经代理访问 Cloudflare 目标时的出口 IP 国家。Cloudflare trace 的 `loc` 是请求所见客户端位置，`colo` 是接收该 trace 请求的数据中心，两者不等于同一个指标。若入口、不同目标或多个地理查询不一致，展示差异并说明用户所需目标是否满足；不要改写为统一地区。

Workers 的 `connect()` 对 Cloudflare IP 有限制；EdgeTunnel 的目标直连失败后可能使用 ProxyIP。核对实际运行版本及设置，再决定其分支；没有运行日志时，机制只能解释现象，不能证明某次请求的内部路径。第三方反代可见目标地址和未加密内容；显式指定 ProxyIP 可能关闭默认兜底。除非用户要求并授权，不更换反代或给所有目标承诺固定出口。

核验后结束自己启动的隔离核心，清理带凭据的临时配置；保留脱敏测速记录。若有失败或区域不足，报告失败次数和最佳实测候选。
