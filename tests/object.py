from unittest import TestCase
from mgit.repo import load_repo
from mgit.object import Blob, pack_obj, write_obj, parse_kvlm, unparse_kvlm
from test_config import test_workpath
import os
import zlib

blob_file_content = b'''1234\n'''
blob_raw = b'blob 5\x001234\n'
blob_sha1 = '81c545efebe5f57d4cab2ba9ec294c4b0cadf672'


class TestBlob(TestCase):
    def setUp(self) -> None:
        self.blob = Blob(load_repo(test_workpath), blob_file_content)

    def test_pack(self) -> None:
        sha, raw = pack_obj(self.blob)
        self.assertEqual(raw, b'blob 5\x001234\n')
        self.assertEqual(sha, '81c545efebe5f57d4cab2ba9ec294c4b0cadf672')

    def test_write(self) -> None:
        write_obj(self.blob)

        path = self.blob.repo.repo_file('objects', blob_sha1[:2], blob_sha1[2:], create=False)
        self.assertTrue(os.path.exists(path))

        with open(path, 'rb') as f:
            raw = zlib.decompress(f.read())
            self.assertEqual(raw, blob_raw)


kvlm_data = b'''tree 7ef4c762de36ab4569c8f8bd0be86c871e68cbc9
author Origami404 <Origami404@foxmail.com> 1613116353 +0800
committer Origami404 <Origami404@foxmail.com> 1613116353 +0800
multiline aaaa
 bbbb
 cccc

Commit Message
'''

kvlm_dct = {
    b'tree': b'7ef4c762de36ab4569c8f8bd0be86c871e68cbc9',
    b'author': b'Origami404 <Origami404@foxmail.com> 1613116353 +0800',
    b'committer': b'Origami404 <Origami404@foxmail.com> 1613116353 +0800',
    b'multiline': b'aaaa\nbbbb\ncccc'
}

kvlm_msg = b'Commit Message\n'


class TestKvlm(TestCase):
    def test_kvlm_parse(self) -> None:
        dct, msg = parse_kvlm(kvlm_data)
        self.assertDictEqual(dct, kvlm_dct)
        self.assertEqual(msg, kvlm_msg)

    def test_kvlm_unparse(self) -> None:
        data = unparse_kvlm(kvlm_dct, kvlm_msg)
        self.assertEqual(data, kvlm_data)
