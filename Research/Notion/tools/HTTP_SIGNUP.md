# HTTP 注册程序

## 2026-10-18 更新：可选人工验证桥接

默认仍为下文所述的纯 HTTP 模式。增加 `--human-verification` 后，仅在 `getLoginOptions` 声明 `challengeProvider=hcaptcha` 时打开一个普通 Edge；不是全程浏览器注册，也不是自动解题。

### 安装与运行

本机需要已安装 Microsoft Edge。可选依赖单独安装，不下载 Chromium：

```powershell
python -m pip install -r Research/Notion/tools/requirements-human-verification.txt

# 直连混合模式
python Research/Notion/tools/http_signup.py --email ACCOUNT_EMAIL --direct --human-verification --human-timeout 180 --deadline 600

# 已配置固定代理环境变量时
python Research/Notion/tools/http_signup.py --email ACCOUNT_EMAIL --proxy-env NOTION_HTTP_PROXY --human-verification --human-timeout 180 --deadline 600
```

### 你需要做什么

1. 程序先通过 HTTP 检查出口和微软邮箱，再获取登录参数。
2. 如进入人工模式，会出现一个独立临时 Edge 窗口。程序在官方注册页填入命令行指定邮箱并提交普通表单；若出现选图等验证，请自行完成，程序不操作题目。
3. **不要在浏览器输入邮件验证码，不要点重发。** 页面成功提交发码后，窗口自动关闭，程序通过微软 Graph 收码并继续 HTTP 登录和引导。
4. 关闭窗口视为取消本轮；人工步骤默认最多 180 秒，同时受总 `--deadline` 约束。

### 衔接规则与限制

- 官方页面自己运行验证并提交一次发码。程序不导出或重放 `challengeToken`，而是接回发码成功响应的 `csrfState` 和本轮 Notion Cookie。
- HTTP 和临时浏览器使用同一代理配置，打开注册页前再次核验出口；若不同就停止，因此轮换出口代理可能不适用。
- 注入本轮 `notion_browser_id` Cookie，严格核对发码邮箱；官方页面可能另生成设备 UUID，桥接保留该原生值并让后续 HTTP 接续。缺失或非法设备字段会停止，不强改官方请求。2026-10-18 真实测试证实初始 Cookie ID 与页面发码设备字段可能不同，二者不可简单画等号。
- 后续 HTTP 使用浏览器请求中的 User-Agent 和客户端版本；这**不代表** HTTP 与 Edge 的 TLS、Canvas 或其他客户端特征完全相同，也不保证站点接受后续请求。
- 浏览器仅负责官方验证和一次发码；阻止浏览器的登录、建空间及完成引导请求，防止用户误操作扩展流程。
- 混合模式仅允许 `--send-attempts 1`。收到发码错误、限流或连接状态不明就关闭并停止，不从 HTTP 再补发一次。
- `--preflight-only` 无论是否同时指定人工开关，都不会打开浏览器或发验证码。
- 普通模式没有后台浏览器依赖；通过开关按需延迟导入 Playwright。只关闭本轮创建的临时窗口，不连接或关闭日常 Edge 窗口。

### 新增留痕与验证边界

- `browser-handoff.private.json`：发码成功后的状态、Cookie、UA 和设备 ID。属于私密会话文件，不分享、不提交 Git。
- `browser-cleanup.json`：context / browser / driver 三项关闭确认；任一未确认则停止后续 HTTP，不将 resourcesClosed 误报为 true。
- 普通事件记录 `browser_opened`、出口核验、一次发码结果、`http_handoff_ready` 和 `browser_closed`，不写 challengeToken 或验证码。
- `requestCount` 统计 Wire 发起的 HTTP 请求；浏览器请求单独记事件，不混作 HTTP 请求总数。
- 上一次真实纯 HTTP 测试在 2026-10-18 11:22 的发码接口收到 400 / `Signup is not allowed.`，不是投递等待超时。**新增混合模式本轮仅做离线模拟，未在真实 Notion 上验证成功。**

```powershell
python -m unittest discover -s Research/Notion/tools -p test_http_signup.py -v
python -m unittest discover -s Research/Notion/tools -p test_human_verification.py -v
```

新增 L1 意图注释记录两项取舍：官方页面仅提交一次发码；按域替换旧 Cookie 避免新旧状态并存。未改写历史诊断结论或 ADR。

## 2026-10-18 真实对照结论

三组对照（每组单次发码、等待 150 秒、全文件夹收码）结果：

- 新邮箱配两个不同代理出口：发码均返回 200，但邮件零投递、验证码未收到。
- 复用旧邮箱配新出口：发码被明确 400 `Signup is not allowed.` 拒绝，且请求不含 challengeToken。
- 说明“200 接受”不等于“邮件已发出”；换出口不改投递结果，重复使用同一邮箱会升级为显式拒绝。
- **完整注册仍未跑通**：卡在邮件投递，不是卡在人机验证或 HTTP 衔接。代理出口信誉是最强嫌疑，但尚未做直连对照，不能作为结论。

详细留痕保存在本地私密目录（含真实 IP 与邮箱，未提交 Git）。

---

以下为默认纯 HTTP 模式说明。

## 状态

- 代码是独立 Python 命令行程序，不导入浏览器库，不启动 Edge、Playwright、CloakBrowser 或终端子进程。
- 按 run12 成功抓包实现请求顺序；**离线模拟通过不等于真实注册成功**。
- 2026-10-18 实际只读检查：第一步 api.ipify.org 连接出现 `ConnectError`，已停止；未发验证码、未创建账号、未启动浏览器。现场留痕位于 `Research/Notion/local/http-signup/20261018T<code>Z-d72de88b/`。
- 本轮没有激活试用或提交支付。Offer 响应仅保存为数据，不据此断言前端显示了几天试用。

## 安装

Python 3.10+，依赖 `httpx>=0.28,<0.29`；没有浏览器依赖。

```powershell
python -m pip install -r Research/Notion/tools/requirements-http-signup.txt
```

## 输入

显式选择一个邮箱，不扫描账号池批量注册。默认从根目录两个账号文件中查找该邮箱：

```text
邮箱----密码----OAuth client_id----refresh_token----辅助邮箱----辅助密码
```

也可传 `--account-file PATH`，支持重复指定。仅使用邮箱、client_id、refresh_token；辅助邮箱不参与收验证码。

## 使用

先做不发码的 HTTP 检查：

```powershell
python Research/Notion/tools/http_signup.py --email ACCOUNT_EMAIL --direct --preflight-only --deadline 60
```

单账号注册：

```powershell
python Research/Notion/tools/http_signup.py --email ACCOUNT_EMAIL --direct --mail-wait 180 --deadline 900
```

若要用已有固定代理，将代理 URL 放在环境变量中，避免出现在进程参数：

```powershell
$env:NOTION_HTTP_PROXY = 'http://PROXY_USER:PROXY_PASSWORD@PROXY_HOST:PROXY_PORT'
python Research/Notion/tools/http_signup.py --email ACCOUNT_EMAIL --proxy-env NOTION_HTTP_PROXY
Remove-Item Env:NOTION_HTTP_PROXY
```

程序不读取系统代理环境变量，不会静默改走其他出口。微软邮箱流量直连；Notion 和出口核验使用同一个显式代理客户端。实际网络联通性需要在运行环境中验证。

## 请求顺序

1. 核验实际出口 IP；失败时发码前停止。
2. 刷新微软 OAuth 凭据，访问 `/me` 核实邮箱归属，读取 inbox + junkemail 建立旧邮件基线。
3. GET 注册入口；尽力从 HTML 识别客户端版本，可用 `--client-version CURRENT_VERSION` 显式覆盖。不伪造浏览器 UA。
4. `getLoginOptions` → `sendTemporaryPassword`，只用本轮新取得的状态和令牌。
5. Graph 会枚举全部邮件文件夹及其子文件夹轮询，只接受新邮件、指定发件域和上下文中的六位码，并按 ID 去重。邮件读取异常不当成“空收件箱”。实测确认只查 inbox/junkemail 会漏掉服务器端规则移动或子文件夹中的邮件。
6. `loginWithEmail` → `authValidate`。
7. 仅对 `isNewSignup=true` 的新用户更新名称、验证建空间权限并创建 `planSelection=team` 工作区（对应第一题“工作”）。不提交 Sales，第二份职业问卷留 `unfilled`。
8. 记录 offers/banner API 响应；调用完成引导接口并检查 `onboarding_completed=true`。

HTTP 不渲染问卷，也不需要点击“跳过”；这里是省略可选职业字段。该省略在真实站点的完整链路尚待实测，不宣称已验证。

## 重试及停止

- 默认只发一次码。可显式 `--send-attempts 3`，上限为首次 + 两次重发；重发只针对“请求接受后，等待时段未观察到邮件”。
- `--mail-wait` 默认 180 秒；`--resend-cooldown` 至少 60 秒；总时限 `--deadline` 默认 900 秒。两者都受总时限限制。
- 限流、交互挑战、发码被服务端拦截、OAuth 错误、网络超时、响应结构变化时停止，不耗完次数、不自动换邮箱/IP。
- 写请求超时可能已在服务端成功，因此不自动重放创建请求。部分成功的工作区 ID 单独保存，避免重复创建。
- 声明 `challengeProvider=hcaptcha` 仅说明验证提供方；发码响应如需交互，程序会停止。没有解题服务、挑战令牌伪造或浏览器回退。
- 每轮使用独立 HTTP Cookie jar 和 deviceId，并非浏览器 Canvas/字体/TLS 指纹伪装。不要将 deviceId 或 UA 数量等同于完整浏览器指纹。

## 留痕与退出

输出默认在 gitignored 的 `Research/Notion/local/http-signup/TIMESTAMP-RANDOM/`：

- `events.jsonl`：请求顺序、状态码、脱敏 JSON 响应、错误种类。非 JSON 仅保存长度和哈希，避免 HTML 内嵌凭据泄露。
- `summary.json`：完成/暂停状态、卡点、出口、设备 ID、请求数及资源释放情况。
- `session.private.json`：本轮会话 Cookie 和用户标识。是私密凭据，不要分享或提交 Git。
- `pending-auth.private.json`：发码后状态，用于人工核查；当前不提供自动恢复 CLI。
- `mail-account.private.json`：微软若返回新的 refresh_token，保存更新后的账号凭据；不覆盖原始账号文件。
- `progress.json`：已创建的工作区 ID；`offers.json`：成功取得的 offer 数据。

普通日志不输出验证码、Cookie、刷新令牌；私密文件会保存必要会话状态。所有 HTTP 客户端通过上下文管理关闭；Ctrl+C 会退出，后续不留浏览器或轮询进程。

退出码：0 完成/只读检查通过；2 输入配置问题；3 外部卡点；4 总时限；5 未预期错误；130 人工中断。Windows PowerShell 宿主可能将非零程序退出归并显示为 1，应以 summary.json 的 exitCode 为准。

## 验证

```powershell
python -m unittest discover -s Research/Notion/tools -p test_http_signup.py -v
```

测试采用 MockTransport，完全不联网，覆盖完整HTTP链路、只读模式不发码、旧码排除、时区、邮箱归属、限流/挑战/网络停机、写请求不重放、部分成功保存、凭据脱敏、Cookie私存和连接关闭。

## 维护注释

本次仅新增两条 L1 意图摘要：写请求超时不重放、发码前建立旧邮件基线。没有重写历史诊断注释，也没有新增 ADR；这些测试不证明 IP、指纹或投递延迟的因果关系。
