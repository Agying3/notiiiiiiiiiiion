# Notion 注册链路研究（已脱敏）

对 Notion 网页版注册流程的黑盒观察记录，以及一个独立的 HTTP 注册实现与测试。

## 内容

```
Research/Notion/
  docs/        研究记录：额度机制、问卷分支、试用差异
  tools/       HTTP 注册实现、人工验证桥接、对照测试
notion-capture2/   注册链路与 hCaptcha 流程的抓包整理
notion-signup-capture.md  早期完整链路记录
```

> 早期的 `Research/Notion/scripts/` 探针脚本未包含在本仓库：它们硬编码了作者本机路径，且依赖已移除的抓包产物，无法独立运行。`tools/` 中的实现已覆盖可复用的部分。

## 主要结论（实测）

- 注册链路：`getLoginOptions` → `sendTemporaryPassword` → 邮件验证码 → `loginWithEmail` → `authValidate` → 资料/工作区创建 → 完成引导。
- `challengeProvider: hcaptcha` 只是提供方声明，不等于必然弹验证；但发码请求可能携带 `challengeToken`。
- **发码返回 200 不代表邮件已投递。** 实测存在「接口接受、邮箱零投递」的情况，需以收件箱实际到信为准。
- 投递与出口 IP 不呈简单因果：更换多个数据中心出口、以及复用曾经成功的出口，结果都可能不同。
- 邮件验证码常见于正文而非标题，读取时应回退到完整正文，并覆盖全部邮件文件夹。
- 纯 HTTP 客户端可能被识别为非浏览器流量并返回 `400 Login is not allowed.`，此时浏览器会话仍可能正常。

## tools 里的实现

- `http_signup.py`：单账号 HTTP 注册主流程，微软 Graph 收码，含脱敏留痕与限时停止。
- `human_verification.py`：可选的人工验证桥接（普通 Edge 经 CDP 附着），仅承担官方验证与一次发码。
- `contrast_test.py`：对照实验驱动，单次发码、独立进程、逐组留痕。
- `test_*.py`：离线测试，不联网、不启动注册。

```powershell
python -m unittest discover -s Research/Notion/tools -p "test_*.py"
```

依赖见 `Research/Notion/tools/requirements-*.txt`。运行注册功能需自备：

- 账号文件：`*-Account.txt`，格式 `邮箱----密码----OAuth client_id----refresh_token----辅助邮箱----辅助密码`
- 代理清单：`proxies.txt`，格式 `主机:端口:用户名:密码`（可直连则不需要）

上述文件均在 `.gitignore` 中，不入库。

## 脱敏说明

本仓库在开源前做过两轮历史重写：

- 移除了抓包截图、原始请求/响应、浏览器 profile、第三方二进制与 `node_modules`；
- 移除了全部真实邮箱、邮箱用户名片段、代理凭据、JWT、会话 Cookie、hCaptcha 令牌、一次性验证码；
- 移除了账号/工作区/设备的持久标识符（UUID 与 32 位十六进制 ID 统一替换为占位符）；
- 移除了真实出口 IP、本地代理端点与作者本机绝对路径；
- 代理商名称与账号文件路径改为通用占位。

**验证口径**：对全部历史提交逐 blob 扫描邮箱、代理凭据、JWT、`token_v2`、`v02:`、`P1_`、UUID、32 位 ID、验证码上下文、绝对路径、代理商名，命中数均为 0。

仓库中不含任何可直接使用的账号、代理或令牌。

## 许可

代码以 **GNU Affero General Public License v3.0** 发布，见 [LICENSE](LICENSE)。

这是强传染性（copyleft）协议：分发修改版必须以同一协议开源；并且**如果把它作为网络服务对外提供**，也必须向使用者提供完整源码（AGPL 第 13 条）。商业使用需同样遵守上述义务。

`notion-capture2/` 与 `notion-signup-capture.md` 为黑盒观察记录，不含厂商源码，随仓库同协议发布。

## 边界

本项目仅用于协议观察与自动化可行性验证。不提供验证码识别或验证绕过服务。第三方服务条款、账号与数据合规由使用者自行负责，详见 [DISCLAIMER.md](DISCLAIMER.md)。
