import struct
from mmap import mmap as Mmap
from mmap import ACCESS_READ
import os
from typing import Any, NamedTuple, List , cast
from .utils import sha_raw_to_str

# 参考: https://docs.python.org/zh-cn/3.8/library/os.html#os.stat_result
class IndexEntry(NamedTuple):
    c_time: int # 32-bit, 上次文件的元信息改变的时间, 单位秒
    c_time_ns: int # 32-bit, 同上, 单位纳秒

    m_time: int # 32-bit, 上次文件改变的时间, 单位秒
    m_time_ns: int # 32-bit, 同上, 单位纳秒

    dev: int  # 32-bit, 该文件所在设备的标识符
    ino: int # 32-bit, 与平台有关，但如果不为零，则根据 st_dev 值唯一地标识文件

    mode: int # 32-bit, 文件模式: 包括文件类型和文件模式位

    uid: int
    gid: int

    size: int
    sha: str # 20-bit, The SHA-1 of the object in a SHa-1 repo

    flags: int # 16-bit flags slipt into (high -> low): 1/1/2/12
    name: bytes

    @property
    def name_length(self) -> int:
        return self.flags & 0x0FFF

    @property
    def assume_valid_flag(self) -> bool:
        return bool(self.flags & 0x8000)
    
    @property
    def extended_flag(self) -> bool:
        return bool(self.flags & 0x4000)
    
    @property
    def stage(self) -> int:
        return self.flags & 0x3000



class IndexFile(NamedTuple):
    version: int
    entry_cnt: int
    entries: List[IndexEntry]


def read_entry(file: Mmap) -> IndexEntry:
    begin = file.tell()
    int_datas = struct.unpack('!10L', file.read(10 * 4))
    sha1_raw  = struct.unpack('!20s', file.read(20))[0]   # for one arg it will return (x, ), so we need [0] to trans it to x
    flags     = struct.unpack('!H', file.read(2))[0]

    length = cast(int, flags) & 0x0FFF
    name = file.read(length)
    
    size_with_padding = (file.tell() - begin + 8) & ~7
    file.read(begin + size_with_padding - file.tell())

    return IndexEntry(*int_datas, sha_raw_to_str(sha1_raw), flags, name) # type: ignore


def read_index(index_path: str) -> IndexFile:
    with open(index_path, 'rb') as file_obj:
        file = Mmap(file_obj.fileno(), 0, access=ACCESS_READ)
        def read_struct(format: str) -> Any:
            '''按大端序(网络字节序)读取格式为 format 的 C 类型'''
            data = file.read(struct.calcsize(format))
            return struct.unpack(f'!{format}', data)

        signature = file.read(4)
        assert signature == b'DIRC'

        version, entry_cnt = struct.unpack('!LL', file.read(2 * 4))
        assert entry_cnt == 2 # type: ignore
        
        entries = [read_entry(file) for i in range(entry_cnt)]

    return IndexFile(version, entry_cnt, entries)