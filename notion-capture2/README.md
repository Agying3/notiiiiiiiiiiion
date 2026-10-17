# Notion 注册流量分类索引

> 对照注册 #2（[REDACTED_EMAIL]，2026-10-17 23:35–23:42）
> 注册 #1 报告见 [notion-signup-capture.md](../notion-signup-capture.md)

## 目录

| 目录 | 内容 | 文件 |
|------|------|------|
| 01-页面加载 | 匿名入口、静态资源、匿名探测(401)、第三方遥测域名清单 | page-load.md |
| 02-请求清单 | （见下：全量请求 URL 列表，因 MCP 落盘失败改为内联记录于各分类文件） | request-index.md |
| 03-hcaptcha | hCaptcha 全生命周期：sitekey、checksiteconfig、hsw.js PoW、getcaptcha、challengeToken | hcaptcha-flow.md |
| 04-注册核心链路 | getLoginOptions → sendTemporaryPassword → loginWithEmail → onboarding 全时序+请求/响应体 | signup-flow.md |
| 05-验证码获取 | 收码方式、账号池状态、邮件要点 | email-code.md |
| 06-cookies | 登录后 61 个 Cookie 全量（Notion 会话/指纹/hCaptcha/Cloudflare/第三方） | cookies-all.md |
| 07-storage | localStorage + sessionStorage（含跨账号残留实证） | storage.md |
| 08-对照总结 | #1 vs #2 对照、注册协议整合、防自动化点、批量注册防关联要点 | comparison.md |

## 数据来源说明

- 网络记录：Playwright MCP browser_network_requests（全量 1282 条，含 946 条静态）
- 请求/响应体：browser_network_request 逐条内联提取
- Cookie：context.cookies() 全量导出
- Storage：page.evaluate 逐键提取
- 已知缺失：getcaptcha/checksiteconfig 响应体为加密 octet-stream 或 MCP 无法回读（已标注）；邮件查看器流量本轮无（用户手动收码）
