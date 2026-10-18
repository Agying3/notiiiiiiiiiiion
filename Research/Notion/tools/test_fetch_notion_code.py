
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 YG
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import fetch_notion_code
from fetch_notion_code import load_account, extract_code, CODE_RE

class FetchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        (root / 'Outlook_37_Account.txt').write_text(
            'demo@example.com----pw----client-id-0001----refresh-token-0002----aux----pw\n',
            encoding='utf-8')
        self._old_root = fetch_notion_code.ROOT
        fetch_notion_code.ROOT = root

    def tearDown(self):
        fetch_notion_code.ROOT = self._old_root
        self.temp.cleanup()

    def test_load_account_finds_email_and_masks_secrets(self):
        account = load_account('demo@example.com')
        self.assertIsNotNone(account)
        self.assertEqual(account['email'], 'demo@example.com')
        self.assertTrue(len(account['client_id']) > 10)
        self.assertNotIn('----', str(account))

    def test_load_account_rejects_unknown(self):
        self.assertIsNone(load_account('nobody@example.com'))

    def test_extract_code_from_notion_mail(self):
        self.assertEqual(extract_code('Your Notion login code', '你的验证码是 384920，10分钟内有效'), '384920')

    def test_extract_code_ignores_non_notion_noise(self):
        self.assertIsNone(extract_code('订单通知', '订单号 384920'))

    def test_six_digit_pattern(self):
        self.assertEqual(CODE_RE.search('code: 384920').group(1), '384920')
        self.assertIsNone(CODE_RE.search('code: 12345'))

if __name__ == '__main__':
    unittest.main()
