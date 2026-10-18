
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 YG
import ast
import tempfile
import unittest
from pathlib import Path
from capture_identity import host_from_legacy, fingerprint_seed, used_hosts_and_ips, reserve_identity


class IdentityTests(unittest.TestCase):
    def test_legacy_registry_extracts_host_without_credentials(self):
        self.assertEqual(host_from_legacy('1.2.3.4:8000:user:secret'), '1.2.3.4')

    def test_seed_is_repeatable_and_changes_with_proxy(self):
        a = fingerprint_seed(3, '1.2.3.4', '123')
        self.assertEqual(a, fingerprint_seed(3, '1.2.3.4', '123'))
        self.assertNotEqual(a, fingerprint_seed(4, '1.2.3.5', '124'))
        self.assertTrue(100000000 <= a < 1000000000)

    def test_registry_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'used_proxies.txt').write_text('1.2.3.4:8000:user:secret\n', encoding='utf-8')
            reserve_identity(root, '3.4.5.6', '13', '198.51.100.9', 4, 'test')
            used = used_hosts_and_ips(root)
            self.assertTrue({'1.2.3.4', '3.4.5.6', '198.51.100.9'} <= used)

    def test_moved_script_root_and_syntax(self):
        path = Path(__file__).with_name('capture_session.py')
        tree = ast.parse(path.read_text(encoding='utf-8'))
        self.assertTrue(tree.body)
        # 仓库根目录由脚本位置推导，不再断言私有文件存在。
        self.assertTrue((path.resolve().parents[3] / 'README.md').is_file())


if __name__ == '__main__':
    unittest.main()
