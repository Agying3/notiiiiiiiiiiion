# Notion 注册链路研究（已脱敏）

对 Notion 网页版注册流程的黑盒观察记录，以及一个独立的 HTTP 注册实现与测试。

## 内容

```
Research/Notion/
  docs/        研究记录：额度机制、问卷分支、试用差异
  scripts/     抓包与探针脚本（需自备浏览器与凭据）
  tools/       HTTP 注册实现、人工验证桥接、测试
notion-capture2/   注册链路与 hCaptcha 流程的抓包整理
notion-signup-capture.md  早期完整链路记录
```

## 主要结论（实测）

- 注册链路：`getLoginOptions` → `sendTemporaryPassword` → 邮件验证码 → `loginWithEmail` → `authValidate` → 资料/工作区创建 → 完成引导。
- `challengeProvider: hcaptcha` 只是提供方声明，不等于必然弹验证；但发码请求可能携带 `challengeToken`。
- **发码返回 200 不代表邮件已投递。** 实测存在「接口接受、邮箱零投递」的情况，需以收件箱实际到信为准。
- 投递与出口 IP 不呈简单因果：更换多个数据中心出口、以及复用曾经成功的出口，结果都可能不同。
- 邮件验证码常见于正文而非标题，读取时应回退到完整正文，并覆盖全部邮件文件夹。

## tools 里的实现

- `http_signup.py`：单账号 HTTP 注册主流程，微软 Graph 收码，含脱敏留痕与限时停止。
- `human_verification.py`：可选的人工验证桥接（普通 Edge 经 CDP 附着），仅承担官方验证与一次发码。
- `contrast_test.py`：对照实验驱动，单次发码、独立进程、逐组留痕。
- `test_*.py`：离线测试，不联网、不启动注册。

```powershell
python -m unittest discover -s Research/Notion/tools -p "test_*.py"
```

依赖见 `Research/Notion/tools/requirements-*.txt`。

## 脱敏说明

本仓库在开源前做过历史重写：

- 移除了抓包截图、原始请求/响应、浏览器 profile、第三方二进制与 `node_modules`；
- 移除了全部真实邮箱、邮箱用户名片段、代理凭据、JWT、会话 Cookie、hCaptcha 令牌、验证码；
- 代理商名称与账号文件路径改为通用占位；
- 重新验证：全历史搜索上述模式均为 0 命中。

仓库中不含任何可直接使用的账号、代理或令牌。脚本中的凭据路径均为占位，运行前需自备。

## 边界

本项目仅用于协议观察与自动化可行性验证。第三方服务条款、账号与数据合规由使用者自行负责。
