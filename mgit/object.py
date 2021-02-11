from abc import abstractmethod, ABC
from typing import Final, Literal
import zlib
from .repo import GitRepo
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
