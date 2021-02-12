from abc import abstractmethod, ABC
from typing import Final, Literal
import zlib
from .repo import GitRepo
from .kvlm import parse_kvlm, unparse_kvlm
import hashlib

GitObjectType = Literal[b'blob', b'commit', b'tree', b'tag']


class GitObject(ABC):
    def __init__(self, repo: GitRepo, data: bytes = None) -> None:
        self.repo = repo

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
    def __init__(self, item_data: bytes) -> None:
        self.deserialize(item_data)

    def deserialize(self, item_data: bytes) -> None:
        self.mode, _, item_data = item_data.partition(b' ')
        self.name, _, self.sha1_raw = item_data.partition(b'\x00')

    def serialize(self) -> bytes:
        return self.mode + b' ' + self.name + b'\x00' + self.sha1_raw

    @property
    def sha1(self) -> str:
        # 大端序
        sha1_int = int.from_bytes(self.sha1_raw, 'big')
        # 去除前导的 0x
        return hex(sha1_int)[2:]


class Tree(GitObject):
    obj_type: Final[GitObjectType] = b'tree'

    def deserialize(self, data: bytes) -> None:
        self.items = list(map(TreeItem, data.split(b'\n')))

    def serialize(self) -> bytes:
        return b'\n'.join(map(lambda item: item.serialize(), self.items))


def pack_obj(obj: GitObject) -> tuple[str, bytes]:
    data = obj.serialize()
    raw = obj.obj_type + b' ' + str(len(data)).encode('ascii') + b'\x00' + data
    sha = hashlib.sha1(raw).hexdigest()

    return sha, raw


def write_obj(obj: GitObject) -> None:
    sha, raw = pack_obj(obj)
    path = obj.repo.repo_file('objects', sha[:2], sha[2:], create=True)

    with open(path, 'wb') as f:
        f.write(zlib.compress(raw))
