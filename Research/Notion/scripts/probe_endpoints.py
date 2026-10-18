# 探测 Notion 内部 v3 接口是否存在的列表（存在返回 400/401，不存在返回 404）
import json, pathlib, time
from curl_cffi import requests as creq

OUT = pathlib.Path(r"REPO_ROOT")
OUT.mkdir(parents=True, exist_ok=True)

CANDIDATES = [
    "getLoginOptions", "sendTemporaryPassword", "loginWithEmail", "sendLoginCode",
    "verifyLoginCode", "signupEmail", "signUp", "createSpace", "completeSignup",
    "getPublicPageData", "getSpaces", "loadUserContent", "getAppConfig", "ping",
    "loadCachedPageChunkV2", "loadPageChunk", "search", "getUserAnalyticsSettings",
    "getSubscriptionData", "getAvailablePlans", "createEmailUser", "resendEmailCode",
    "verifyEmailCode", "sendEmailCode", "checkEmail", "getSignupOptions",
    "createUser", "registerUser", "joinSpace", "acceptInvitation", "logout",
    "getNotificationSettings", "getOnboardingState", "setOnboardingState",
    "getUserSettings", "updateUserSettings", "createWorkspace", "getWorkspace",
    "syncRecordValues", "enqueueTask", "getTasks", "submitTransaction",
]

BASE = "https://app.notion.com/api/v3/"
sess = creq.Session(impersonate="chrome")
HEAD = {
    "Content-Type": "application/json",
    "Notion-Client-Version": "23.13.20261017.1134",
    "Notion-Audit-Log-Platform": "web",
    "Origin": "https://app.notion.com",
    "Referer": "https://app.notion.com/signup",
}

results = []
for ep in CANDIDATES:
    try:
        r = sess.post(BASE + ep, json={}, headers=HEAD, timeout=20)
        body = r.text
        results.append({"endpoint": ep, "status": r.status_code, "body": body[:300]})
    except Exception as e:
        results.append({"endpoint": ep, "status": -1, "error": repr(e)[:160]})
    time.sleep(0.6)

(OUT / "endpoint-probe.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

exists = [r for r in results if r["status"] not in (404, -1)]
missing = [r for r in results if r["status"] == 404]
print(f"EXISTS {len(exists)} / MISSING {len(missing)}\n")
for r in results:
    tag = "MISS " if r["status"] == 404 else ("ERR  " if r["status"] == -1 else "OK   ")
    name = ""
    try:
        name = json.loads(r["body"]).get("name", "")
    except Exception:
        pass
    print(f'{tag} {r["status"]:>4}  {r["endpoint"]:32s} {name}')
