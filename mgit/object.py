from abc import abstractmethod, ABC
from typing import Final, Literal, Tuple, List
import zlib
from .repo import GitRepo
from .kvlm import parse_kvlm, unparse_kvlm
from .utils import sha_raw_to_str
import hashlib

GitObjectType = Literal[b'blob', b'commit', b'tree', b'tag']


class GitObject(ABC):
    def __init__(self, data: bytes = None) -> None:
        if data:
            self.deserialize(data)

    @abstractmethod
    def deserialize(self, data: bytes) -> None:
        raise NotImplementedError()

    @abstractmethod
    def serialize(self) -> bytes:
        raise NotImplementedError()

    @property
    @abstractmethod
    def obj_type(self) -> GitObjectType:
        raise NotImplementedError


class Blob(GitObject):
    obj_type: Final[GitObjectType] = b'blob'

    def deserialize(self, data: bytes) -> None:
        self.data = data

    def serialize(self) -> bytes:
        return self.data


class Commit(GitObject):
    obj_type: Final[GitObjectType] = b'commit'

    def deserialize(self, data: bytes) -> None:
        self.dct, self.msg = parse_kvlm(data)

    def serialize(self) -> bytes:
        return unparse_kvlm(self.dct, self.msg)


class TreeItem:
    '''储存 Tree Object 里的一个条目'''
    def __init__(self, mode: bytes, name: bytes, sha1_raw: bytes) -> None:
        self.mode = mode
        self.name = name
        self.sha1_raw = sha1_raw

    def serialize(self) -> bytes:
        return self.mode + b' ' + self.name + b'\x00' + self.sha1_raw

    @property
    def sha1(self) -> str:
        return sha_raw_to_str(self.sha1_raw)


class Tree(GitObject):
    obj_type: Final[GitObjectType] = b'tree'

    def deserialize(self, data: bytes) -> None:
        self.items: List[TreeItem] = []
        item_beg = 0

        # 每个 TreeItem 之间没有分隔符
        while True:
            # 找到每一个 TreeItem 用于分隔 文件名 的 空格
            name_beg = data.find(b' ', item_beg)
            mode = data[item_beg : name_beg]      # mode 可能是 5 位或 6 位

            # 找到每一个 TreeItem 用于分隔 SHA-1 的 NUL 字符
            sha_beg = data.find(b'\x00', item_beg)
            name = data[name_beg+1 : sha_beg]       # 文件名可以任意长 (name_beg+1 以跳过分隔符)

            # 加上 SHA-1 的 二进制格式的长度+1 作为 item 的尾后指针
            item_end = sha_beg + 21
            sha1_raw = data[sha_beg+1 : item_end]   # SHA-1 的二进制格式必为 20 位 (sha_beg+1 以跳过分隔符)

            # 若找不到 name 了就退出
            if name_beg == -1:
                break

            # 解析成 TreeItem 并设置新的 item 的开始
            self.items.append(TreeItem(mode, name, sha1_raw))
            item_beg = item_end

    def serialize(self) -> bytes:
        return b''.join(map(lambda item: item.serialize(), self.items))


class Tag(GitObject):
    obj_type: Final[GitObjectType] = b'tag'

    def deserialize(self, data: bytes) -> None:
        self.dct, self.msg = parse_kvlm(data)

    def serialize(self) -> bytes:
        return unparse_kvlm(self.dct, self.msg)

def pack_obj(obj: GitObject) -> Tuple[str, bytes]:
    data = obj.serialize()
    raw = obj.obj_type + b' ' + str(len(data)).encode('ascii') + b'\x00' + data
    sha = hashlib.sha1(raw).hexdigest()

    return sha, raw


def write_obj(repo: GitRepo, obj: GitObject) -> None:
    sha, raw = pack_obj(obj)

    with repo.open_object(sha, create=True) as f:
        f.write(zlib.compress(raw))


def unpack_obj(raw: bytes) -> GitObject:
    obj_type, _, raw = raw.partition(b' ')
    lenght, _, data = raw.partition(b'\x00')

    assert lenght == str(len(data)).encode('ascii')

    if obj_type == 'blob':
        return Blob(data)
    elif obj_type == 'tree':
        return Tree(data)
    elif obj_type == 'commit':
        return Commit(data)
    else:
        raise RuntimeError(f'Unsupport Object Type: {obj_type.decode("ascii")}')


def read_obj(repo: GitRepo, sha: str) -> GitObject:
    with repo.open_object(sha, create=False) as f:
        return unpack_obj(zlib.decompress(f.read()))
