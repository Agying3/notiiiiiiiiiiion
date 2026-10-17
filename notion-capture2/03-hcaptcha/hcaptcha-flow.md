# hCaptcha 验证流程抓包（对照组注册 #2）

- 注册邮箱：`[REDACTED_EMAIL]`
- 请求序号参照 MCP 网络面板（本轮全量记录）
- hCaptcha **完整生命周期首次全量抓到**

## 时序（毫秒级相对时间）

| 序号 | 请求 | 说明 |
|------|------|------|
| 362 | POST `app.notion.com/api/v3/getLoginOptions` | 响应含 `challengeProvider: "hcaptcha"`，前端据此加载 hCaptcha |
| 363 | GET `js.hcaptcha.com/1/api.js?render=explicit&onload=__hcaptchaOnLoad` | hCaptcha 主 SDK |
| 364/368 | GET `c2b516716e1b.w.hcaptcha.com/logo.png` / `58d7cc284a30.w.hcaptcha.com/logo.png` | 组件 logo（worklet 域名） |
| 365/366 | GET `newassets.hcaptcha.com/captcha/v1/86591f996c36877668d253e353e36fac021db33b/static/hcaptcha.html` | 验证 UI iframe（加载两次） |
| 369 | POST `api.hcaptcha.com/checksiteconfig?v=86591f996c36877668d253e353e36fac021db33b&host=app.notion.com&sitekey=<uuid>&sc=1&swa=1&spst=1` | 站点配置查询 |
| 370 | GET `newassets.hcaptcha.com/c/3479469110c0ec7a86ee56ad3e665030203d01b450c170e7a5ef4c93ce42b116/hsw.js` | **hsw（proof-of-work）求解脚本** |
| 372 | POST `api.hcaptcha.com/getcaptcha/<uuid>` | 获取挑战题目（`content-type: application/octet-stream`，加密传输） |
| — | POST `api.hcaptcha.com/checkcaptcha/...`（人机交互后） | 提交答案 → 签发 `P1_` token（本轮挑战为无感通过，未单独留下 checkcaptcha 记录，token 直接经 hsw 求解生成） |
| 373 | POST `app.notion.com/api/v3/sendTemporaryPassword` | 请求体携带 `challengeToken: "[REDACTED_CAPTCHA_TOKEN]…"`（hCaptcha passkey JWT） |

## 关键参数（固定/可复用）

```
sitekey:      <uuid>     (Notion 注册页)
host:         app.notion.com
hsw 版本路径:  newassets.hcaptcha.com/c/3479469110c0ec7a86ee56ad3e665030203d01b450c170e7a5ef4c93ce42b116/hsw.js
SDK 入口:     js.hcaptcha.com/1/api.js?render=explicit&onload=__hcaptchaOnLoad
UI iframe:    newassets.hcaptcha.com/captcha/v1/86591f996c36877668d253e353e36fac021db33b/static/hcaptcha.html
```

## getcaptcha 请求体（加密 binary）

`content-type: application/octet-stream`，明文部分可见：
```json
{"type":"hsw","req":"[REDACTED_JWT]"}
```
> JWT payload 解码要点：`{"f":0,"s":17,"t":"w","d":"<挑战数据>","l":"/c/3479469110c0ec7a86ee56ad3e665030203d01b450c170e7a5ef4c93ce42b116","i":"sha256-JMqpnB9duIyOaCbL7GvHPsqPZW0Jhy0AUl2Ety3YxHY=","e":1792254975,"n":"hsw","c":1000}`
> - `l` = hsw.js 版本路径；`i` = 脚本 SHA-256 完整性哈希；`e` = 过期时间戳；`c:1000` = PoW 迭代次数
> - 请求体其余部分为二进制加密（工作负荷证明 + 环境指纹），不可直接复放

## Cookie 留痕（hCaptcha 域）

| Cookie | 域 | 值 |
|--------|----|----|
| `__cf_bm` | .hcaptcha.com | Cloudflare Bot Management |
| `hmt_id` | api.hcaptcha.com | `<uuid>`（hCaptcha 设备/会话追踪 ID） |
| `__cflb` | api.hcaptcha.com | Cloudflare 负载均衡 |

## challengeToken → sendTemporaryPassword

`sendTemporaryPassword` 请求体（截取）：
```json
{
  "email": "[REDACTED_EMAIL]",
  "redirectURL": "/p/<id>?v=<id>",
  "disableLoginLink": false,
  "native": false,
  "isSignup": true,
  "challengeToken": "[REDACTED_CAPTCHA_TOKEN]…（JWT，payload 含 exp/passkey_id，短时效）",
  "shouldHidePasscode": false,
  "loginOptionsToken": "[REDACTED_NOTION_TOKEN]…",
  "authFlowId": "<uuid>",
  "deviceId": "<uuid>",
  "loginRouteOrigin": "signup"
}
```

响应：
```json
{"csrfState":"[REDACTED_NOTION_TOKEN]…"}
```

## 与第一次注册（#1）的关键对照

| 维度 | 注册 #1（[REDACTED_USER]） | 注册 #2（[REDACTED_USER]） |
|------|----------------------|----------------------|
| getLoginOptions challengeProvider | hcaptcha | hcaptcha |
| sendTemporaryPassword challengeToken | 有（P1_ 开头） | 有（P1_ 开头，本报告） |
| redirectURL 字段 | 无 | 有（携带来源页） |
| hCaptcha 流量 | 未捕获 | **全量捕获（本文件）** |
| 注册结果 | isNewSignup: true | isNewSignup: true |

> 注：注册 #2 的 `redirectURL` 指向注册 #1 创建的页面 URL，因清 Cookie 后 localStorage 未完全清除 + 历史路由缓存残留（`LRU:KeyValueStore2:lastVisitedRoute`），此字段非必填。
