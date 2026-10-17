# Business 额度 + 试用能不能后补

> 时间：2026-10-18 00:30

---

## 一、Business 到底多少额度？

### 短答：**没有"次数"，只有"双窗口 + 天花板"，而且 Notion 不公布具体数字**

我把官方帮助中心的额度页逐句读完了，能确认的只有机制，没有数字：

| 维度 | 事实 |
| --- | --- |
| 计量方式 | **两个窗口**：6 小时滚动窗口 + 月度窗口（跟随计费周期） |
| 用完会怎样 | 部分 AI 功能**暂停**，6 小时窗口自动恢复；月度用完要等下个计费周期 |
| 能不能超支 | 默认不能。admin 可以打开「Allow workspace to use Notion credits after AI limit is reached」，开了之后超出的部分**扣 credits** |
| 哪些功能计入 | 个人 Notion Agent（含 chat）、图片生成、页面翻译 |
| 哪些**不**计入 | **AI Meeting Notes**（独立 10 小时/天上限）、**Custom Agents / Workers**、**Premium 模型**（后两者直接烧 credits） |

**官方从头到尾没有给出"多少次"或"多少 token"的数字**，只说"an allowance"。这是产品策略：额度会随负载动态调整，写死了反而被动。

### 能从代码里确认的间接信息

`promotions.aiCredits` 里有个 `maxAllowance`：

```js
maxAllowance: { free: 500, paid: 2500 }
```

`paid: 2500` 是**付费 workspace 的 credits 余额天花板**，不是 allowance。两者是不同池子：

- **allowance** = 套餐内含，不计费，用完暂停
- **credits** = 额外买的（$10/1000），按 provider 原价扣

所以 Business 的实际可用量 = **allowance（不透明）+ credits 余额（上限 2500）**。

### 想拿到真实数字，只能实测

唯一可靠办法：开一个 Business（试用即可），进 `Settings → Notion AI → Usage`，那个页面会显示用量条。用脚本定期读这个页面的数值，反推出 allowance 总量。

---

## 二、注册完没选，后面还能选吗？

### 分三种情况，答案不同

#### 情况 A：问卷没填（直接跳过 / 关掉了）

**能补。** 代码里有一整套 onboarding 状态管理：

```js
postOnboardingRedirectURL
onboardingFormResponseId / SecretKey / SpaceId / SpaceIntent
isResettingOnboarding
devOnboardingPlanTypeOverride     // 开发环境强制指定套餐
devSkipOnboardingToComplete
```

`isResettingOnboarding` 这个 key 的存在说明** onboarding 是可以重跑的**。UI 上也有入口：

```js
"continueOnboardingQuestFromSidebar"   // 侧边栏继续引导
"onboardingQuestRegistry"              // 引导任务注册表
"SidebarTrialButton"                   // 侧边栏试用按钮
```

所以：**没填 ≠ 永久放弃**。侧边栏会留引导入口，或者从 `Settings` 里能找到 onboarding 重启。

#### 情况 B：填了 `school`（学生）

**基本不能改回。** 原因：

1. 问卷提交后，`onboardingFormSpaceIntent` 会存到 sessionStorage 并同步到服务端（`spaceIntent`）
2. 这个 intent 决定后续走哪条产品轨（edu vs business）
3. `school` 一旦写入，账号被打上 edu 候选标记，**business trial 的资格判定会直接 ineligible**
4. 即使你把问卷重填成 `work`，服务端记录的首次 intent 大概率不会被覆盖（这是典型的"首答定轨"设计，防止用户反复刷福利）

#### 情况 C：填了 `work`/`personal`/`life` 但当时没点「开始试用」

**能补，而且入口很多。** 代码里的入口：

```js
"start_business_trial"          // 主动开始
"start_business_trial_mwn"      // 移动端变体
"SidebarTrialButton" / "SidebarTrial"    // 侧边栏常驻按钮
"trial_home"                    // 试用主页
"BusinessTrialModalStore"       // 弹窗状态机
"PostBusinessTrialDelayedOfferModal"     // 试用过期后的追销
"businessTrialLossAversionModal" // 快过期挽留
```

关键判断：**试用是"可后补"的**。`BusinessTrialModalStore` 是个 store（状态机），不是一次性弹窗——只要资格还在，它会一直能被触发。`SidebarTrialButton` 更是常驻。

---

## 三、还有个坑：试用只有一次

39 条 campaign 里，`*_stacked_*` 系列（叠加试用）都是给**已在 Plus 的人**再叠 Business 用的，不是给新号的第二次机会。

对纯新号来说，能拿的就是 `business_reverse`（30 天）或 `business_cc`（30 天，要绑卡）这两类。**同一 workspace 用完一次，不会再给第二次。**

但注意：**workspace 级别，不是账号级别**。一个账号可以有多个 workspace，每个 workspace 各自独立判试用。代码里的 `space_switcher_stacked_business_trial_*` 就是这个逻辑的体现。

---

## 四、实操建议

| 目标 | 问卷怎么填 | 后续动作 |
| --- | --- | --- |
| 要 30 天 Business 试用 | `work`（最稳） | 进去后点侧边栏 Trial 按钮，或等首页弹窗 |
| 已经填错成 school | — | 换新 workspace（同账号可建新 workspace），新 workspace 重新走 onboarding |
| 想要教育版免费 Plus | `school` + 学校邮箱验证 | 走 `/notify-for-student-orgs-apply` 或教育版入口 |
| 只是想试 AI | `work`，不点试用也行 | 先用 complimentary 额度，用完再点试用 |

---

## 五、还需要你提供的信息（要实测才准）

1. **Business allowance 的真实数字** —— 必须进一个 Business workspace 看 `Settings → Notion AI → Usage` 那个页面
2. **问卷接口名** —— 前端没有硬编码问卷文案（走服务端下发），所以接口名要抓包才知道
3. **试用按钮在你现有三个号上还在不在** —— #1 #2 如果没点试用，现在侧边栏应该还有 Trial 按钮

第 3 点你现在就能验证：**登录 #1 或 #2，看左侧栏底部有没有试用入口**。有 → 说明可后补；没有 → 说明弹窗过期就收回。

---

## 六、留痕

```
captures/web/allowance.txt              # 双窗口机制、计入/不计入清单、10h meeting cap
captures/web/pricing-faq.txt            # "Limited Trial" 标记、credits 价格
captures/web/billing.txt                # 官方"有没有免费试用"的答复
scripts/grep_trial_entry.py             # 试用入口检索
scripts/list_trial_ui.py                # 试用 UI 组件清单
scripts/grep_reset_onboarding.py        # onboarding 重置 key
scripts/grep_intent.py                  # intent 存储 key
```
