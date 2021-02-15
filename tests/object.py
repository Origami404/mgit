from unittest import TestCase
from mgit.repo import load_repo
from mgit.object import Blob, Tree, TreeItem, pack_obj, write_obj
from test_config import test_workpath
import os
import zlib

blob_file_content = b'''1234\n'''
blob_raw = b'blob 5\x001234\n'
blob_sha1 = '81c545efebe5f57d4cab2ba9ec294c4b0cadf672'


class TestBlob(TestCase):
    def setUp(self) -> None:
        self.repo = load_repo(test_workpath)
        self.blob = Blob(blob_file_content)

    def test_pack(self) -> None:
        sha, raw = pack_obj(self.blob)
        self.assertEqual(raw, b'blob 5\x001234\n')
        self.assertEqual(sha, '81c545efebe5f57d4cab2ba9ec294c4b0cadf672')

    def test_write(self) -> None:
        write_obj(self.repo, self.blob)

        path = self.repo.repo_file('objects', blob_sha1[:2], blob_sha1[2:], create=False)
        self.assertTrue(os.path.exists(path))

        with open(path, 'rb') as f:
            raw = zlib.decompress(f.read())
            self.assertEqual(raw, blob_raw)


class TestCommit(TestCase):
    # Too simple to test
    pass


tree_file_content = [
    # 100644 blob 9c9ddc2cc36ec58f5fc76c7c5157cfc046dd79ea    c.txt
    b'\x31\x30\x30\x36\x34\x34\x20\x63\x2e\x74\x78\x74\x00\x9c\x9d\xdc\x2c\xc3\x6e\xc5\x8f\x5f\xc7\x6c\x7c\x51\x57\xcf\xc0\x46\xdd\x79\xea',

    # 100644 blob 81c545efebe5f57d4cab2ba9ec294c4b0cadf672    a.txt
    # 040000 tree fe7ce18c5d359042f6eb43e81cf7119240dd3681    b
    b'\x31\x30\x30\x36\x34\x34\x20\x61\x2e\x74\x78\x74\x00\x81\xc5\x45\xef\xeb\xe5\xf5\x7d\x4c\xab\x2b\xa9\xec\x29\x4c\x4b\x0c\xad\xf6\x72\x34\x30\x30\x30\x30\x20\x62\x00\xfe\x7c\xe1\x8c\x5d\x35\x90\x42\xf6\xeb\x43\xe8\x1c\xf7\x11\x92\x40\xdd\x36\x81'
]


class TestTree(TestCase):
    def setUp(self) -> None:
        self.item = Tree(tree_file_content[0]).items[0]
        self.tree = Tree(tree_file_content[1])

    def assertItemEqual(self, item1: TreeItem, mode: bytes, name: bytes, sha1: str) -> None:
        self.assertEqual(item1.mode, mode)
        self.assertEqual(item1.name, name)
        self.assertEqual(item1.sha1, sha1)

    def test_tree_item(self) -> None:
        self.assertItemEqual(self.item, b'100644', b'c.txt', '9c9ddc2cc36ec58f5fc76c7c5157cfc046dd79ea')
        self.assertEqual(self.item.serialize(), tree_file_content[0])

    def test_tree(self) -> None:
        items = self.tree.items

        self.assertItemEqual(items[0], b'100644', b'a.txt', '81c545efebe5f57d4cab2ba9ec294c4b0cadf672')
        self.assertItemEqual(items[1], b'40000', b'b',     'fe7ce18c5d359042f6eb43e81cf7119240dd3681')

        self.assertEqual(self.tree.serialize(), tree_file_content[1])