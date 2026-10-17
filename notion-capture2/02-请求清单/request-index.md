# 注册 #2 全量 API 请求清单（按序号）

> 序号 = MCP 网络面板索引（static:false 视角 + 关键静态）
> 946 条纯静态资源（_assets/*.js/css/png/woff）不在本表，见 01-页面加载

## 匿名阶段
| # | Method | URL | Status |
|---|--------|-----|--------|
| 115 | POST | /api/v3/getUserSharedPagesInSpace | 401 |
| 116 | POST | /api/v3/getAppConfig | 200 |
| 134 | POST | /api/v3/getSpacesInitial | 401 |
| 137 | POST | /api/v3/ping | 200 |
| 139 | POST | /api/v3/getUserAnalyticsSettings | 200 |
| 210 | POST | /api/v3/authValidate | 401 |
| 233 | POST | /api/v3/syncRecordValuesMain | 200 |
| 238 | POST | /api/v3/getUserAnalyticsSettings | 200 |
| 251 | POST | /api/v3/getLifecycleUserProfile | 401 |
| 295 | POST | /api/v3/authValidate | 401 |

## 注册核心（详见 04-注册核心链路）
| # | Method | URL | Status | 关键内容 |
|---|--------|-----|--------|---------|
| 361 | POST | /api/v3/getAssetsJsonV2 | 200 | |
| 362 | POST | /api/v3/getLoginOptions | 200 | challengeProvider=hcaptcha |
| 364/368 | GET | *.w.hcaptcha.com/logo.png | 200 | |
| 369 | POST | api.hcaptcha.com/checksiteconfig | 200 | sitekey=b3fa1b6e-… |
| 372 | POST | api.hcaptcha.com/getcaptcha/b3fa1b6e-… | 200 | octet-stream 加密挑战 |
| 373 | POST | /api/v3/sendTemporaryPassword | 200 | 带 P1_ challengeToken → csrfState |
| 382 | POST | /api/v3/loginWithEmail | 200 | state+<code> → isNewSignup:true |
| 385 | POST | /api/v3/authValidate | 200 | x-notion-user-id 确认 |
| 387 | POST | /api/v3/initializeUserAnalyticsEmptySync | 200 | |

## 邮箱域校验批
| # | URL |
|---|-----|
| 462 | isUserDomainJoinable |
| 463 | isEmailEducation |
| 464 | validateUserCanCreateWorkspace |
| 465 | getVerifiedEmailDomain |
| 466 | getGeoIpLocation |
| 565 | getJoinableSpaces |
| 566-570 | 上批重复一轮 |

## 登录后初始化 + Onboarding
| # | URL | 说明 |
|---|-----|------|
| 602 | getSpacesInitial | 200（已登录） |
| 605 | getLoginOptions | |
| 617 | getLifecycleUserProfile | 200 |
| 618 | getAppConfig | |
| 636 | saveTransactionsMain | onboarding 写事务 |
| 668 | updateCurrentUserProfile | {"name":"[REDACTED_USER]"} |
| 679 | createSpace | 工作区 ff681333-… |
| 682 | getPublicSpaceData | |
| 684 | getBillingData | |
| 685 | getFeatureBillingData | |
| 693 | getUserHomePages | |
| 698 | getSubscriptionData | |
| 699/700 | getVisibleUsers / getSimilarUsers | |
| 721 | getAIUsageEligibilityV2 | |
| 733 | getSubscriptionEntitlements | |
| 740/741 | inAppGetTemplateByBlockId ×2 | 模板拉取 |
| 742 | getLibraryPage | |
| 743 | scheduleSetupPeopleCollection | People 集合 |
| 744 | getTeamsV2 | |
| 754 | getUserNotificationsInitial | |
| 760 | getUserTasks | |
| 778/779 | enqueueTask ×2 | 异步任务 |
| 784/804/1257… | getTasks | 任务轮询 |
| 785 | loadBlockSubtree | |
| 796 | getAvailableModels | |
| 797 | runInferenceTranscript | AI 首轮对话 |
| 798 | scheduleOnboardingGtmEntityArtifact | |
| 799 | completeCurrentUserOnboarding | 完成 |
| 811 | getThreadSpaceId | |

## AI 对话页持续
| # | URL |
|---|-----|
| 1215-1282 | getEmailDomainSettings / getIsCalendarUser / listAIConnectors / getInferenceTranscriptsForUser / checkFeatureGate / warmScriptAgentDynamicModuleCache / warmCustomAgentNudgePrecheck / recordAgentThreadView / markInferenceTranscriptSeen / getIsMailUser / getPossibleOffers / getInferenceTranscriptsUnreadCount / getAvailableModels / getAIUsageEligibilityV2 / getCreditRateLimitStatus / saveTransactions*(多次) / syncRecordValues*(多次) / etClient(多次) / getTasks(多次) |

## 静态关键项
| # | URL |
|---|-----|
| 363 | js.hcaptcha.com/1/api.js?render=explicit&onload=__hcaptchaOnLoad |
| 365/366 | newassets.hcaptcha.com/captcha/v1/86591f99…/static/hcaptcha.html |
| 370 | newassets.hcaptcha.com/c/3479469110c0ec7a…/hsw.js |
