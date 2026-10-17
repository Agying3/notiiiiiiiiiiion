import ast
import tempfile
import unittest
from pathlib import Path
from capture_identity import host_from_legacy, fingerprint_seed, used_hosts_and_ips, reserve_identity


class IdentityTests(unittest.TestCase):
    def test_legacy_registry_extracts_host_without_credentials(self):
        self.assertEqual(host_from_legacy('[REDACTED_PROXY] '1.2.3.4')

    def test_seed_is_repeatable_and_changes_with_proxy(self):
        a = fingerprint_seed(3, '1.2.3.4', '123')
        self.assertEqual(a, fingerprint_seed(3, '1.2.3.4', '123'))
        self.assertNotEqual(a, fingerprint_seed(4, '1.2.3.5', '124'))
        self.assertTrue(100000000 <= a < 1000000000)

    def test_registry_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'used_proxies.txt').write_text('[REDACTED_PROXY] encoding='utf-8')
            reserve_identity(root, '3.4.5.6', '13', '9.9.9.9', 4, 'test')
            used = used_hosts_and_ips(root)
            self.assertTrue({'<ip>', '<ip>', '2.3.4.5', '8.8.8.8', '3.4.5.6', '9.9.9.9'} <= used)

    def test_moved_script_root_and_syntax(self):
        path = Path(__file__).with_name('capture_session.py')
        tree = ast.parse(path.read_text(encoding='utf-8'))
        self.assertTrue(tree.body)
        self.assertTrue((path.resolve().parents[3] / 'agent.md').is_file())


if __name__ == '__main__':
    unittest.main()
