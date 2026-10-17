# 注册 #2 核心注册链路（API 时序 + 请求/响应体）

- 邮箱：`[REDACTED_EMAIL]`
- userId：`<uuid>`
- 时间：2026-10-17 23:35–23:42 (Asia/Shanghai)
- 状态：注册成功，工作区已建立

## 阶段 1：页面加载（清 Cookie 全匿名）

| # | 请求 | 说明 |
|---|------|------|
| 1-2 | GET notion.so/signup → 301 → app.notion.com/signup | 匿名入口 |
| ~100 | GET `_assets/*.js/css` 全部 chunk | 前端资源 |
| 116 | POST `/api/v3/getAppConfig` | 客户端配置 |
| 134/210/295 | POST `/api/v3/getSpacesInitial` / `authValidate` / `getLifecycleUserProfile` → **401** | 匿名状态探测（401 = 未登录，正常） |
| 137 | POST `/api/v3/ping` | 心跳启动 |
| 139/238/335 | POST `/api/v3/getUserAnalyticsSettings` | 分析设置 |

## 阶段 2：邮箱提交 + hCaptcha + 发码（核心）

### #362 POST getLoginOptions
```json
// 请求
{"email":"[REDACTED_EMAIL]","requireWorkTypeEmail":false}
// 响应
{"hasAccount":true,"samlSignIn":"unavailable","passwordSignIn":false,
 "mustReverify":false,
 "loginOptionsToken":"[REDACTED_NOTION_TOKEN]…",
 "challengeProvider":"hcaptcha",
 "authFlowId":"<uuid>"}
```
> `hasAccount: true` —— 即便全新邮箱也返回 true（Notion 对所有邮箱统一返回，不泄露账号存在性）

### hCaptcha 环节（详见 03-hcaptcha/hcaptcha-flow.md）
- sitekey `<uuid>`
- 本轮挑战通过 → 签发 challengeToken（`P1_` JWT）

### #373 POST sendTemporaryPassword
```json
// 请求
{"email":"[REDACTED_EMAIL]",
 "redirectURL":"/p/<id>?v=<id>",
 "disableLoginLink":false,"native":false,"isSignup":true,
 "challengeToken":"[REDACTED_CAPTCHA_TOKEN]…（hCaptcha passkey）",
 "shouldHidePasscode":false,
 "loginOptionsToken":"[REDACTED_NOTION_TOKEN]…（来自 #362）",
 "authFlowId":"<uuid>",
 "deviceId":"<uuid>",
 "loginRouteOrigin":"signup"}
// 响应
{"csrfState":"[REDACTED_NOTION_TOKEN]…"}
```
> **注意**：`deviceId` = `notion_browser_id` Cookie 值（9055129d-…），即设备指纹在页面加载时生成、随发码请求上报

### 邮箱域校验批（#462-466）
`isUserDomainJoinable` / `isEmailEducation` / `validateUserCanCreateWorkspace` / `getVerifiedEmailDomain` / `getGeoIpLocation` —— 并行判定

## 阶段 3：验证码登录

### #382 POST loginWithEmail
```json
// 请求
{"state":"[REDACTED_NOTION_TOKEN]…（sendTemporaryPassword 的 csrfState）",
 "password":"<code>",        // 邮件 6 位码
 "appSource":"notion",
 "loginRouteOrigin":"signup"}
// 响应
{"isNewSignup":true,"userId":"<uuid>"}
```
> 成功 Set-Cookie：`token_v2`（537 字符 JWT）、`notion_user_id`、`notion_users`、`__Host-session_binding`、`csrf`、`file_token`（新出现的文件凭证）

### #385 POST authValidate → 200
响应头 `x-notion-user-id: <uuid>`（**验证归属的可靠信号**）

## 阶段 4：Onboarding

| # | API | 请求体 |
|---|-----|--------|
| 636 | `saveTransactionsMain` | onboarding 写事务 |
| 668 | `updateCurrentUserProfile` | `{"name":"[REDACTED_USER]"}` |
| 679 | `createSpace` | `{"name":"[REDACTED_USER]的工作空间","icon":"📚","planType":"personal","planSelection":"school","initialPersona":"unfilled","domainType":"personal","deviceId":"<uuid>","deviceType":"web-desktop","source":"handle_root_redirect","createSpaceView":true}` |
| 682-700+ | `getBillingData`/`getFeatureBillingData`/`getVisibleUsers` 等 | 计费/套餐初始化 |
| 740/741 | `inAppGetTemplateByBlockId` ×2 | **新发现**：onboarding 模板按 blockId 拉取 |
| 743 | `scheduleSetupPeopleCollection` | 建 People 集合 |
| 778/779 | `enqueueTask` ×2 | 异步任务入队 |
| 797 | `runInferenceTranscript` | AI 首轮对话（chat?t=<id>） |
| 799 | `completeCurrentUserOnboarding` | 完成 onboarding |

## 工作区信息
- spaceId：`<uuid>`
- shortId：`34681877272`
- 计划：`personal` / planSelection `school`
- 落地：`app.notion.com/chat?t=<id>`

## 公共请求头（与 #1 一致）
```
content-type: application/json
notion-client-version: 23.13.20261017.1134
notion-audit-log-platform: web
user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) … Chrome/155 …
referer: https://app.notion.com/signup
sentry-trace / baggage（Sentry 链路追踪）
```
