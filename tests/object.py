from unittest import TestCase
from mgit.repo import load_repo
from mgit.object import Blob, pack_obj, write_obj
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
