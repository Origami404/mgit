from unittest import TestCase
from mgit.kvlm import parse_kvlm, unparse_kvlm


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
