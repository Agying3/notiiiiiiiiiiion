# Notion 注册流程抓包报告

- 时间：2026-10-17 22:58–23:01 (Asia/Shanghai)
- 浏览器：Playwright MCP（Edge 155 / Chromium 155, Windows）
- 注册页：`https://www.notion.so/signup` → 301 → `https://app.notion.com/signup`
- 注册邮箱：`[REDACTED_EMAIL]`（注册成功，userId `<uuid>`）
- 补充抓取（23:19 第二轮）：hCaptcha 资源、Cookie/Storage 全量、邮件查看器流程

## 〇、hCaptcha 验证流程（第一轮报告缺失，本轮补全）

getLoginOptions 响应 `challengeProvider: "hcaptcha"` → 前端加载 hCaptcha 组件 → 人机验证通过后签发
`challengeToken`（`[REDACTED_CAPTCHA_TOKEN]…`，JWT 形态，含 exp/passkey claims，短时效）→ 随 `sendTemporaryPassword` 提交。
**注意**：本轮抓包未捕获 hCaptcha 自身域名流量（`*.hcaptcha.com`），推测发生在用户手动操作时段（第一轮浏览器被用户接管完成验证码）或被 MCP 拦截漏记。已知事实：无 challengeToken 则 sendTemporaryPassword 必被拒。hCaptcha 站点密钥在页面 HTML/JS 中（`data-sitekey`），复刻时需先从 signup 页源码提取。

## 〇-B、临时密码邮件获取流程（第一轮报告缺失，本轮补全）

用户在**同一浏览器的另一个标签页**（微软邮件查看器 https://wr-imap.cheapemail.cc/ ）收到 6 位验证码 `<code>`：
- 该查看器为第三方 Hotmail/Outlook IMAP 网页端，轮询 `/api/v1/health` 与 `/api/v1/limits`（约每 10s）
- 6 位码来自 Notion 发送的系统邮件（标题含"登录 Notion"），人工读取后填回 signup 页
- 完整请求列表见 `wr-imap.cheapemail.cc` 域名下的 32 条记录（1-32，含 app.js/config.js/style.css）

## 一、页面加载阶段

| # | 请求 | 说明 |
|---|------|------|
| 1-2 | GET notion.so/signup → 301 → app.notion.com/signup | 入口重定向 |
| 3-112 | GET `_assets/*.js/css`（约 110 个 chunk） | 前端资源，含 `login-*.js`、`transport-support-*.js` |
| 113 | POST `/api/v3/getAppConfig` | 客户端配置；请求头带 `notion-client-version: 23.13.20261017.1134` |
| 114 | POST `exp.notion.com/v1/initialize` | Statsig 实验 SDK 初始化（k=client-Tgza5w…） |
| 117/124/257 | POST `http-inputs-notion.splunkcloud.com/services/collector/raw` | Splunk 日志上报 |
| 121 | POST `/api/v3/getUserAnalyticsSettings` | 匿名用户分析设置 |
| 122+ | POST `/api/v3/ping`（持续心跳，约每 10s） | 会话保活 |
| 123 | GET `/f/refresh` | 前端刷新检查 |
| 279/332 | POST `/api/v3/etClient` | 事件批处理上报（et = event trail） |
| 250-351 | GTM/FB/Twitter/LinkedIn/Bing/Clarity/metadata.io | 第三方营销像素（AW-954804604、GTM-MTWKTL4、FB 499229960464487 等） |
| 309-319 | `accounts.google.com/gsi/*` | Google 一键登录 FedCM 预取 |
| 312 | GET `api.ipify.org/?format=json` | 客户端出口 IP 采集 |
| 329 | POST `o324374.ingest.sentry.io` | Sentry 错误监控 |

## 二、邮箱提交阶段（核心注册 API）

### 1) 检查登录选项 — POST `/api/v3/getLoginOptions`
```json
// 请求
{"email":"[REDACTED_EMAIL]","requireWorkTypeEmail":false}
// 响应
{"hasAccount":true,"samlSignIn":"unavailable","passwordSignIn":false,
 "mustReverify":false,
 "loginOptionsToken":"[REDACTED_NOTION_TOKEN]…（一次性令牌）",
 "challengeProvider":"hcaptcha",
 "authFlowId":"<uuid>"}
```

### 2) 发送临时密码（登录码）— POST `/api/v3/sendTemporaryPassword`
```json
// 请求
{"email":"[REDACTED_EMAIL]","disableLoginLink":false,"native":false,
 "isSignup":true,
 "challengeToken":"[REDACTED_CAPTCHA_TOKEN]…（hCaptcha Passkey token，JWT 形态）",
 "shouldHidePasscode":false,
 "loginOptionsToken":"[REDACTED_NOTION_TOKEN]…（来自上一步）",
 "authFlowId":"<uuid>",
 "deviceId":"<uuid>",
 "loginRouteOrigin":"signup"}
// 响应
{"csrfState":"[REDACTED_NOTION_TOKEN]…（state 令牌，用于下一步换码登录）"}
```
> `challengeToken` 是 hCaptcha（challengeProvider=hcaptcha）通过后签发的通行证；无 hCaptcha 或过期则此接口会被拒。

### 3) 邮箱域名校验批（并行 7 连发）
输入邮箱后前端同时打：
`isUserDomainJoinable` / `isEmailEducation` / `validateUserCanCreateWorkspace` / `getVerifiedEmailDomain` / `getGeoIpLocation` / `checkEmailEligibilityForConnectedAppProducts` / `getJoinableSpaces`
（请求体均为 `{}` 或含 email，判定企业域加入、教育优惠、GeoIP 归属、可建工作区）

### 4) 邮箱码登录 — POST `/api/v3/loginWithEmail`
```json
// 请求
{"state":"[REDACTED_NOTION_TOKEN]…（sendTemporaryPassword 返回的 csrfState）",
 "password":"<code>",            // 邮件里的 6 位临时登录码
 "appSource":"notion",
 "loginRouteOrigin":"signup"}
// 响应
{"isNewSignup":true,"userId":"<uuid>"}
```
> 成功后 Set-Cookie 下发会话（token_v2 / notion_user_id 等），并跳转 onboarding。

### 5) 会话校验 — POST `/api/v3/authValidate` 请求 `{}` 响应 `{}`（200 = 会话有效）

## 三、Onboarding 建号阶段

| # | API | 请求体要点 |
|---|-----|-----------|
| 410 | `getSpacesInitial` | 拉取初始空间数据 |
| 495 | `saveTransactionsMain` | Notion 事务式写入（onboarding 问答进度） |
| 741 | `updateCurrentUserProfile` | `{"name":"[REDACTED_USER]"}` 设置用户名 |
| 757 | `createSpace` | `{"name":"[REDACTED_USER]的工作空间","icon":"💼","planType":"team","planSelection":"team","initialPersona":"unfilled","domainType":"personal","deviceId":"6307e105-…","deviceType":"web-desktop","source":"handle_root_redirect","createSpaceView":true}` 建工作区 |
| 760-870 | `getBillingData` / `getFeatureBillingData` / `getPossibleOffers` / `getSubscriptionEntitlements` / `getAIUsageEligibilityV2` 等 | 计费/套餐/AI 配额初始化 |
| 879-900 | `saveTransactionsFanout` | onboarding 向导每一步的写事务 |
| 921 | `completeCurrentUserOnboarding` | 完成 onboarding |
| 908/909 | `getAvailableModels` / `runInferenceTranscript` | Notion AI 首次对话（chat?t=<id>） |

## 四、注册协议总结（可直接脚本化复刻的顺序）

1. GET `https://www.notion.so/signup`（拿 cookie：`blocale`、cf 等）
2. POST `getAppConfig`（版本头 `notion-client-version` 必带）
3. POST `getLoginOptions` `{email}` → 拿 `loginOptionsToken` + `authFlowId`
4. hCaptcha（challengeProvider=hcaptcha）通过拿 `challengeToken`
5. POST `sendTemporaryPassword`（email + 两个 token + authFlowId + deviceId）→ 拿 `csrfState`
6. 从邮箱收件箱取 6 位码
7. POST `loginWithEmail` `{state: csrfState, password: 6位码}` → 200 即注册成功，Set-Cookie 会话
8. `authValidate` 验活 → `updateCurrentUserProfile`（名字）→ `createSpace`（工作区）→ `completeCurrentUserOnboarding`

### 关键防自动化点
- **hCaptcha**：`sendTemporaryPassword` 强制 `challengeToken`（P1_ 开头 JWT，含 exp/passkey claims）
- **deviceId**：UUID，随 `sendTemporaryPassword` / `createSpace` 上报
- **一次性令牌链**：`loginOptionsToken` → `challengeToken` → `csrfState`，三段串联且短时效
- **心跳**：`/api/v3/ping` 每 ~10s 一次，Sentry trace（baggage 头）随每个请求
- **指纹外围**：ipify 出口 IP、Splunk/GTM/Clarity 像素、Statsig 实验分组全部随页面加载先行

### 公共请求头（API 调用必需）
```
content-type: application/json
notion-client-version: 23.13.20261017.1134
notion-audit-log-platform: web
x-notion-active-user-header: (空；登录后为 userId)
user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) … Chrome/155 …
referer: https://app.notion.com/signup
```
（请求还随带 Sentry trace 头：`sentry-trace` + `baggage`，非必需）

## 五、Cookie 全量留痕（登录成功后 app.notion.com / notion.com 域）

### 会话核心（脚本复用即需这几个）
| Cookie | 域 | 属性 | 说明 |
|--------|----|------|------|
| `token_v2` | .app.notion.com | httpOnly, Secure, Lax, 1 年 | **会话凭证**（v03%3AeyJhbGci… JWT 形态，537 字符），复刻登录只需此 |
| `notion_user_id` | .app.notion.com | Secure, Lax, 1 年 | `<uuid>` |
| `notion_users` | .app.notion.com | Secure, Lax, 1 年 | `["3fcd872b-…"]` URL 编码数组 |
| `__Host-session_binding` | app.notion.com | httpOnly, Secure, Lax, 1 年 | 会话绑定（设备指纹关联） |
| `csrf` | .app.notion.com | Secure, Lax, 1 天 | CSRF token（UUID） |
| `device_id` | .app.notion.com | httpOnly, Secure, Lax, 1 年 | **设备指纹**（httpOnly，脚本不可读）`4b5c65db-d332-4fc2-8aa2-…` |

### 设备/浏览器标识（注册前置）
| Cookie | 说明 |
|--------|------|
| `notion_browser_id` (.notion.com, 1 年) | 浏览器指纹 `6307e105-8928-4aa8-951c-…`（与请求体 deviceId 一致，**httpOnly=false，localStorage 可见**） |
| `STATSIG_LOCAL_STORAGE_STABLE_ID` (localStorage) | Statsig 稳定 ID `<uuid>` |
| `notion_check_cookie_consent` | `false` |
| `NEXT_LOCALE` / `notion_locale` | `zh-CN` |
| `_cioid` | 无连字符 userId（3fcd872b594c818d85d70002…，32 字符） |

### 第三方/CDN
| Cookie | 说明 |
|--------|------|
| `__cf_bm` (.notion.so & .notion.com) | Cloudflare Bot Management（30 分钟滚动） |
| `_cfuvid` (.notion.com) | Cloudflare 唯一访客 ID |
| `__ps_r/__ps_sr/__ps_did/__ps_fva/__ps_lu/__ps_slu` (.notion.so) | PageSense/像素同步（6 个） |
| `g_state` + `onetap_nonce` (app.notion.com) | Google One Tap FedCM 状态（本会话未使用） |

### 关键时序点
- `notion_browser_id`（指纹）在**页面加载即写入**，注册前就存在 → 新号注册必须先过 Cloudflare `__cf_bm` + 指纹采集
- `token_v2` 等 6 个会话 Cookie 在 `loginWithEmail` 响应一次性 Set-Cookie 下发
- `device_id`（httpOnly）与 `notion_browser_id`（公开）**值不同**：前者服务端关联，后者客户端上报 deviceId

## 六、Storage 留痕

### localStorage（关键键）
- `AMP_notion` — 混合分析 SDK 状态：`{"deviceId":"<id>","userId":"<id>","sessionId":1792249112839,…}`
- `eventTrailBufferByInstanceID:[…]AMP_unsent_notion` — **待上报事件缓冲区**（27KB，含完整行为轨迹）
- `gist.web.userToken` — gist（增长团队 SDK）token `3fcd872b594c818d…`，带 30 天 expiry
- `gist.web.sessionId` — 会话 ID
- `LRU:KeyValueStore2:lastKnownAppJsVersion` — 前端版本记录 [23,13,20261017,1134]
- `LRU:KeyValueStore2:current-user-id` / `lastVisitedRouteSpaceId` — 路由状态缓存
- `boot:gate:*` / `boot:exp:*` — Statsig 功能门控本地缓存
- `LRU:KeyValueStore2:recent_events_g8vbhx` — 近期事件（create_database from workflow_templa…）

### sessionStorage（注册路径直接相关）
- `signupMethod: "other"` + `signupMethodTimestamp: "1792249250564"` — **注册方式标记**（"other" = 邮箱注册，非 Google/Microsoft/ChatGPT SSO）
- `urlAnalytics` — UTM 全为 none（无渠道归因）
- `sessionTabId` / `tcms` / `tcmu` — 会话/标签标识

## 七、注册成功后的路由跳转链（第一轮报告缺失，本轮补全）

1. `/signup`（邮箱+验证码）→ `loginWithEmail` 200 →
2. `app.notion.com/chat?t=<id>`（AI onboarding 对话页）→
3. `app.notion.com/`（onboarding 问答：姓名/用途/团队规模）→
4. `app.notion.com/p/<id>?v=<id>&t=<id>`（最终落地：数据库视图页，即 onboarding 模板创建的默认任务/笔记页）

相关 API：`createSpace`（工作区 id `<uuid>`，shortId `56465176514`）→ `scheduleSetupPeopleCollection`（建 People 集合）→ `enableTeams` → `runInferenceTranscript`（AI 首轮对话）→ `completeCurrentUserOnboarding`
