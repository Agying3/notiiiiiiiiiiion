# Notion 注册对照抓包报告（#1 vs #2 总结）

## 两次注册概况

| 维度 | 注册 #1 | 注册 #2 |
|------|---------|---------|
| 邮箱 | [REDACTED_EMAIL] | [REDACTED_EMAIL] |
| userId | <uuid> | <uuid> |
| spaceId | <uuid> | <uuid> |
| 验证码 | <code> | <code> |
| hCaptcha | 有（未捕获流量） | 有（全量捕获） |
| 计划 | team | personal/school |
| 结果 | 成功 | 成功 |

## 注册协议（两次对照验证，确定流程）

```
1. GET  notion.so/signup → 301 → app.notion.com/signup
   （Cookie: __cf_bm/_cfuvid 下发；notion_browser_id 页面加载即写）

2. POST /api/v3/getAppConfig                → 客户端配置
3. POST /api/v3/getUserAnalyticsSettings    → 分析设置（匿名）

4. POST /api/v3/getLoginOptions
   请求: {"email":"<邮箱>","requireWorkTypeEmail":false}
   响应: {loginOptionsToken, authFlowId, challengeProvider: "hcaptcha"}
   注意: hasAccount 恒为 true，不泄露存在性

5. hCaptcha 流程（sitekey: <uuid>）
   a. GET  js.hcaptcha.com/1/api.js
   b. POST api.hcaptcha.com/checksiteconfig  → 站点配置
   c. GET  newassets.hcaptcha.com/c/<hash>/hsw.js  → PoW 求解脚本
   d. POST api.hcaptcha.com/getcaptcha/<sitekey>   → 挑战（octet-stream 加密）
   e. （人机验证 / PoW 完成）→ 签发 challengeToken（P1_ JWT，短时效）

6. POST /api/v3/sendTemporaryPassword
   请求: {email, disableLoginLink:false, native:false, isSignup:true,
          challengeToken: "P1_…", shouldHidePasscode:false,
          loginOptionsToken, authFlowId, deviceId, loginRouteOrigin:"signup"}
   响应: {csrfState: "[REDACTED_NOTION_TOKEN]…"}
   deviceId = notion_browser_id cookie 值
   （并行: isUserDomainJoinable/isEmailEducation/validateUserCanCreateWorkspace/
           getVerifiedEmailDomain/getGeoIpLocation/getJoinableSpaces 邮箱域校验批）

7. 邮件收 6 位码（IMAP/Graph/手动）

8. POST /api/v3/loginWithEmail
   请求: {state: <csrfState>, password: "<6位码>", appSource:"notion", loginRouteOrigin:"signup"}
   响应: {"isNewSignup":true,"userId":"…"}
   Set-Cookie: token_v2 + notion_user_id + notion_users + __Host-session_binding
              + csrf + file_token + device_id + notion_sync_user_id + _cioid
   响应头 x-notion-user-id（authValidate）= 归属确认

9. POST /api/v3/authValidate → 200
10. Onboarding:
    updateCurrentUserProfile {name}
    createSpace {name:"<用户名>的工作空间", icon, planType, planSelection,
                 initialPersona:"unfilled", domainType:"personal", deviceId,
                 deviceType:"web-desktop", source:"handle_root_redirect", createSpaceView:true}
    inAppGetTemplateByBlockId ×2（模板拉取）
    scheduleSetupPeopleCollection / enqueueTask / enableTeams
    runInferenceTranscript（AI 首轮对话）
    completeCurrentUserOnboarding
```

## 防自动化点（两次注册实证）

1. **hCaptcha challengeToken 硬门槛**：sendTemporaryPassword 无有效 P1_ token 必拒。本轮实证其链路：checksiteconfig → hsw.js（PoW，c=1000 迭代）→ getcaptcha（加密挑战）→ token 签发。token 短时效（exp 数分钟）且绑定 passkey_id。
2. **deviceId/notion_browser_id**：页面加载即生成，随 sendTemporaryPassword 与 createSpace 上报。httpOnly 的 device_id 与公开的 notion_browser_id 值不同、分工不同。
3. **一次性令牌链**：loginOptionsToken → challengeToken → csrfState，三段串联、短时效、单次有效。
4. **心跳 + 遥测前置**：/api/v3/ping ~10s 一次；Splunk/Statsig/AMP/gist 全套在注册前已上报（含 sessionId、device 指纹）。
5. **Cookie+localStorage 双层指纹**：清 Cookie 不清 localStorage —— AMP sessionId、spaceCellMapping 跨账号残留，可作多账号关联检测信号（服务端侧对应 session_binding）。

## 批量注册防关联要点（两轮对照结论）

- 每号必须新 BrowserContext（非同 context 清 cookie），否则 localStorage 的 AMP sessionId / 空间映射表直接暴露关联
- notion_browser_id 每次加载新生成（可控），但 __Host-session_binding 为服务端下发绑定，无法客户端重置
- hCaptcha hmt_id + __cf_bm 在 hcaptcha.com 域持久，跨注册累积风控画像 —— 每号需清或隔离 hcaptcha 域 cookie
- 出口 IP：Notion 用 getGeoIpLocation + api.ipify.org 双重采集；Cloudflare __cf_bm 绑定 IP+UA
- signupMethod=other / signupMethodTimestamp 写入 sessionStorage，作为服务端事件的时间锚点

## 文件索引

```
notion-capture2/
├── 03-hcaptcha/hcaptcha-flow.md      ← hCaptcha 全生命周期（首次完整捕获）
├── 04-注册核心链路/signup-flow.md     ← API 时序 + 请求/响应体
├── 06-cookies/cookies-all.md          ← 61 个 Cookie 全量（含 identity/msgstore 新发现）
├── 07-storage/storage.md             ← localStorage/sessionStorage（跨账号残留实证）
└── 08-对照总结/comparison.md          ← 本文件

notion-signup-capture.md               ← 注册 #1 报告（含 Cookie/Storage 第五节起）
```

## #2 新发现的接口（#1 报告未记录）

- `inAppGetTemplateByBlockId` ×2 — onboarding 模板按 blockId 拉取
- `enqueueTask` / `getTasks` — 异步任务队列（模板实例化走后台任务）
- `loadBlockSubtree` — 页面子树加载
- `getThreadSpaceId`、`recordAgentThreadView`、`markInferenceTranscriptSeen` — AI 对话线程管理
- `identity.notion.com` 域（auth_sync_message_accountSwitcher）
- `msgstore-002.app.notion.com`（Socket.io + AWS ALB）
- `getDesktopAppRegistration`、`getCreditRateLimitStatus` — 桌面端注册/AI 额度
