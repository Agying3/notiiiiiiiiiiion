
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 tujue
import unittest
from pathlib import Path
from direct_capture_options import options


class DirectTests(unittest.TestCase):
    def test_ordinary_browser_without_proxy_or_fingerprint(self):
        config=options(Path('test-output'), {'HTTP_PROXY':'http://example.test','https_proxy':'http://example.test','ALL_PROXY':'socks5://example.test','PATH':'keep'})
        self.assertEqual(config['channel'],'msedge')
        self.assertIsNone(config['proxy'])
        self.assertEqual(config['args'],['--no-proxy-server'])
        self.assertEqual(config['env'],{'PATH':'keep'})
        self.assertEqual(config['record_har_mode'],'full')


if __name__=='__main__':
    unittest.main()
