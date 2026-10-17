# -*- coding: utf-8 -*-
"""指纹浏览器 + 代理验证：启动 CloakBrowser，走 proxyprovider 代理，输出指纹与出口 IP"""
import sys, random, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from cloakbrowser import launch

# 从代理列表取一个（ip:port:user:pass）
PROXY_LINE = "[REDACTED_PROXY]
parts = PROXY_LINE.strip().split(":")
host, port, user, pwd = parts[0], parts[1], parts[2], parts[3]
proxy_url = f"http://{user}:{pwd}@{host}:{port}"

seed = random.randint(10**6, 10**9)
print(f"[+] seed={seed} proxy={host}:{port}")

browser = launch(
    headless=False,          # 你要看得到
    humanize=True,
    proxy=proxy_url,
    args=[f"--fingerprint={seed}"],
)
try:
    page = browser.new_page()
    page.goto("https://api.ipify.org/?format=json", wait_until="domcontentloaded", timeout=60000)
    print("[+] exit IP:", page.inner_text("body"))
    page.goto("https://httpbin.org/headers", wait_until="domcontentloaded", timeout=60000)
    print("[+] headers:", page.inner_text("body")[:500])
    print("[+] OK — 指纹浏览器 + 代理正常。浏览器保持打开 5 分钟供检查")
    page.wait_for_timeout(300000)
finally:
    browser.close()
