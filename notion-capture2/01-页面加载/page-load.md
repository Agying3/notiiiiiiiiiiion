# 注册 #2 页面加载与第三方遥测（阶段 0 留痕）

- 序号参照 MCP 网络面板全量记录（含 946 条静态请求）
- 匿名状态（Cookie 清空）从 notion.so/signup 进入

## 页面导航
| # | 请求 | 状态 |
|---|------|------|
| 1 | GET https://www.notion.so/signup | 301 |
| 2 | GET https://app.notion.com/signup | 200 |
| — | 页面 title: "Notion - 注册"（zh-CN，NEXT_LOCALE=zh-CN） | |

## 前端资源
- `_assets/*.js/css` 约 100+ chunk（ClientFramework、login-*.js、transport-support-*.js、mainApp-*.js 等）
- 首屏导航耗时 15232ms（navigation API 实测，含全部 chunk）

## 匿名探测（401 正常，未登录）
| # | API | 状态 |
|---|-----|------|
| 115 | getUserSharedPagesInSpace | 401 |
| 134 | getSpacesInitial | 401 |
| 210 | authValidate | 401 |
| 251 | getLifecycleUserProfile | 401 |
| 295 | authValidate | 401 |

## 心跳/遥测
- `/api/v3/ping`（~10s 间隔持续）
- `/api/v3/etClient`（事件批处理，323/331/344/352/353…）
- `/api/v3/getUserAnalyticsSettings`（多次）
- `/api/v3/getAssetsJsonV2`

## 第三方域名（匿名加载阶段即全量启动）
| 域名 | 用途 |
|------|------|
| exp.notion.com | Statsig 实验（/v1/initialize、/v1/rgstr） |
| http-inputs-notion.splunkcloud.com | Splunk 日志 |
| o324374.ingest.sentry.io | Sentry 错误监控 |
| aif.notion.com | 内嵌分析 iframe |
| api.ipify.org | 出口 IP 采集 |
| www.googletagmanager.com | GTM（GTM-MTWKTL4、AW-954804604 等多 ID） |
| googleads.g.doubleclick.net / www.google.com/pagead | Google Ads 转化 |
| connect.facebook.net / www.facebook.com | FB 像素（499229960464487） |
| t.co / analytics.twitter.com | Twitter 像素 |
| snap.licdn.com / px.ads.linkedin.com | LinkedIn 像素（pid 2368700） |
| bat.bing.com / c.bing.com | Bing UET（343272399） |
| scripts.clarity.ms / f.clarity.ms | MS Clarity |
| cdn.metadata.io | metadata.io |
| cdn.cr-relay.com | Customer.io relay |
| wcs.naver.com | **Naver 广告（#2 新记录）** |
| accounts.google.com/gsi | Google One Tap FedCM 预取 |
| bzr.openai.com | **ChatGPT SSO 按钮预取（#2 新记录）** |

## 关键响应头（安全配置，全 API 一致）
```
strict-transport-security: max-age=31536000; includeSubDomains; preload
x-frame-options: SAMEORIGIN
x-content-type-options: nosniff
content-security-policy: default-src 'none'
referrer-policy: strict-origin-when-cross-origin
server: cloudflare（cf-ray: *-NRT 东京节点）
```
