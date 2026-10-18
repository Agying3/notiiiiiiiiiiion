import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from fetch_notion_code import load_account, extract_code, CODE_RE

class FetchTests(unittest.TestCase):
    def test_load_account_finds_email_and_masks_secrets(self):
        account = load_account('[REDACTED_EMAIL]')
        self.assertIsNotNone(account)
        self.assertEqual(account['email'], '[REDACTED_EMAIL]')
        self.assertTrue(len(account['client_id']) > 10)
        self.assertNotIn('----', str(account))

    def test_load_account_rejects_unknown(self):
        self.assertIsNone(load_account('nobody@example.com'))

    def test_extract_code_from_notion_mail(self):
        self.assertEqual(extract_code('Your Notion login code', '你的验证码是 <code>，10分钟内有效'), '<code>')

    def test_extract_code_ignores_non_notion_noise(self):
        self.assertIsNone(extract_code('订单通知', '订单号 <code>'))

    def test_six_digit_pattern(self):
        self.assertEqual(CODE_RE.search('code: <code>').group(1), '<code>')
        self.assertIsNone(CODE_RE.search('code: 12345'))

if __name__ == '__main__':
    unittest.main()
