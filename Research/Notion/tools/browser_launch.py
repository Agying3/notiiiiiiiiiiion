# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 tujue
"""统一的浏览器启动入口：默认用普通 Edge，仅当安装了 CloakBrowser 才启用指纹模式。

早期抓包脚本直接 `from cloakbrowser import ...`，导致这个仓库在没装该商业工具时
完全跑不起来。这里做一层适配：没有 CloakBrowser 就退回 Playwright 自带的 Edge，
并丢弃 CloakBrowser 专有的 `--fingerprint=` 参数与 `humanize` 选项。
"""
from __future__ import annotations

from typing import Any

try:  # pragma: no cover - 取决于本机是否安装商业指纹浏览器
    from cloakbrowser import launch as _launch
    from cloakbrowser import launch_persistent_context as _launch_persistent_context

    HAVE_CLOAKBROWSER = True
except ImportError:  # 开源默认路径：只用普通 Edge
    HAVE_CLOAKBROWSER = False
    _driver = None

    def _playwright() -> Any:
        global _driver
        if _driver is None:
            from playwright.sync_api import sync_playwright

            _driver = sync_playwright().start()
        return _driver

    def _normalize(kwargs: dict) -> dict:
        # 这些是 CloakBrowser 专有参数，普通 Edge 会直接报错。
        kwargs.pop('args', None)
        kwargs.pop('humanize', None)
        kwargs.setdefault('channel', 'msedge')
        return kwargs

    def _launch_persistent_context(user_data_dir, **kwargs):
        return _playwright().chromium.launch_persistent_context(str(user_data_dir), **_normalize(kwargs))

    def _launch(**kwargs):
        return _playwright().chromium.launch(**_normalize(kwargs))


def launch_persistent_context(user_data_dir, **kwargs):
    return _launch_persistent_context(user_data_dir, **kwargs)


def launch(**kwargs):
    return _launch(**kwargs)


def mode_note() -> str:
    return 'CloakBrowser 指纹模式' if HAVE_CLOAKBROWSER else '普通 Edge（未安装 CloakBrowser，已忽略指纹参数）'
