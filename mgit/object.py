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


# 从 Python 3.7 开始, 内置的 dict 类型已经保证有序了
def parse_kvlm(data: bytes) -> tuple[dict[bytes, bytes], bytes]:
    dct = {}                    # 要返回的 key-value 列表的对应字典
    lines = data.split(b'\n')   # 将输入按行分隔

    key, value_lines = b'', []  # 当前的 key 与 value(按行分隔)
    message_begin = -1          # message 的起始行

    # Parse key-value list
    for idx, line in enumerate(lines):
        # 如果一行以空格前导, 那么它是上一行 value 的一部分
        if line.startswith(b' '):
            value_lines.append(line[1:])
            continue

        # 如果其不以空格前导, 那么它可能是一个新的 key-value 对
        # 先将上一个 key-value 对加入 dct
        if key != b'':
            dct[key] = b'\n'.join(value_lines)

        # 如果这行是个空行, 那么它是 key-value 列表与 message 的分隔行.
        # 记录 message 的起始行并 break
        if line == b'':
            message_begin = idx + 1
            break

        # 如果不是空行, 那么它是一个新的 key-value 对
        # 按第一个空格将其分为 key 和 value 的第一行
        key, _, value = line.partition(b' ')
        value_lines = [value]

    # Parse message
    assert message_begin != -1
    message = b'\n'.join(lines[message_begin:])

    return dct, message


def unparse_kvlm(dct: dict[bytes, bytes], message: bytes) -> bytes:
    lines = []
    for key, value in dct.items():
        # value 里的回车在下一行要加前导空格以转义
        escaped_value = value.replace(b'\n', b'\n ')
        lines.append(key + b' ' + escaped_value)

    lines.append(b'')
    lines.append(message)

    return b'\n'.join(lines)
