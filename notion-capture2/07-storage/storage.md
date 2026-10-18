# 注册 #2 Storage 留痕（localStorage + sessionStorage）

## sessionStorage（注册路径直接相关）

| 键 | 值 | 说明 |
|----|----|------|
| `signupMethod` | `other` | **注册方式标记**（邮箱注册 = other；Google/MS/ChatGPT SSO 会是其他值） |
| `signupMethodTimestamp` | `1792251398626` | 注册方式写入时间戳（2026-10-17 23:36:38） |
| `sessionTabId` | `<uuid>` | 标签页会话 ID |
| `sessionAppRefreshed` | `false` | 是否刷新 |
| `gist.web.isPersistingSession` | `true` | gist（增长团队）会话持久化标记 |

## localStorage（关键键）

### 会话/身份
| 键 | 值 |
|----|----|
| `gist.web.userToken` | `{"value":"<id>","expiry":"2026-11-16T15:36:38.649Z"}` |
| `gist.web.sessionId` | `<uuid>` |
| `LRU:KeyValueStore2:current-user-id` | `<uuid>` |
| `AMP_notion` | `{"deviceId":"<id>","userId":"<id>","sessionId":1792249112839,…}` |

### 工作区路由
| 键 | 值 |
|----|----|
| `LRU:KeyValueStore2:lastVisitedRouteSpaceId` | （推断）`<uuid>` |
| `LRU:KeyValueStore2:spaceIdToShortId` | `{"<uuid>":"34681877272", …}` |
| `LRU:KeyValueStore2:spaceCellMapping` | `{"space-short-id:56465176514":"prod-space-apne1-0001","space-id:3a6d2596-37c2-…":"…}` |
> **注意**：`spaceCellMapping` 同时含 #1 工作区（prod-space-usw2-0001）与 #2（apne1-0001）—— 清 Cookie 不清 localStorage 的直接证据，跨账号状态残留

### 版本/门控
| 键 | 值 |
|----|----|
| `LRU:KeyValueStore2:lastKnownAppJsVersion` | `[23,13,20261017,1134]` |
| `boot:gate:*` / `boot:exp:*` | Statsig 门控缓存 |

### 其他
- `theme`：`{"mode":"light"}`
- `contrast`：`{"mode":"standard"}`
- `LRU:LocalPreferenceStore3:guest:queryParamsRedirect` — 来源页参数
- `BlockFrecency`、`sidebar*`、`searchFrecency` 等使用习惯缓存

## 与 #1 对照

| 键 | #1 | #2 |
|----|----|----|
| `signupMethod` | other | other |
| `AMP_notion.sessionId` | 1792249112839 | 1792249112839（**相同！** 清 Cookie 未清 localStorage，AMP 会话跨注册保留） |
| `spaceCellMapping` | 仅 #1 工作区 | #1 + #2 工作区共存 |

**观察**：`clearCookies()` 不清 localStorage。因此 localStorage 中的会话痕迹会跨会话保留，这也解释了站点为何能据此识别同一来源。
