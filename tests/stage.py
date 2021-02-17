from unittest import TestCase
from mgit.stage import parse_entry, parse, IndexEntry, IndexFile
from mmap import mmap as Mmap
from mmap import ACCESS_READ
import os

entry_item_path = os.path.join('tests', 'index-data', 'entry')
index_path = os.path.join('tests', 'index-data', 'index')

class TestEntryItem(TestCase):
    def setUp(self) -> None:
        with open(entry_item_path, 'rb') as f:
            self.item = parse_entry(Mmap(f.fileno(), 0, access=ACCESS_READ))

        self.index = parse(index_path)

    def test_entry_item(self) -> None:
        self.assertTupleEqual(self.item, IndexEntry(
            c_time=1613116341, c_time_ns=88079769,
            m_time=1613116341, m_time_ns=88079769,
            dev=2050, ino=5243019,
            mode=33188, uid=1000, gid=1000,
            size=5, sha='81c545efebe5f57d4cab2ba9ec294c4b0cadf672',
            flags=5, name=b'a.txt'
        ))
        self.assertEqual(self.item.name_length, 5)
        self.assertFalse(self.item.assume_valid_flag)
        self.assertFalse(self.item.extended_flag)
        self.assertEqual(self.item.stage, 0)

    def test_index(self) -> None:
        self.assertEqual(self.index.version, 2)
        self.assertEqual(self.index.entry_cnt, 2)

        # TODO: Add entries test