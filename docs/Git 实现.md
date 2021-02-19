# Git 实现

## 个人总结 & 阅读指南

Git 的设计理念其实深受 Unix 哲学的影响: 

- 将文件系统本身作为一个 键值对数据库
- 数据本身作为文本流而存储/处理 (虽然并非完全如此)
- 并不使用专门的数据结构以压缩存储空间, 而是使用文本+泛用的压缩算法
- 后端结构非常简单, (但对用户前端的抽象没做好emmm), 核心算法简单到基本不可能有错
- 暴露出可以访问底层结构的命令行接口
- 数据储存使用分隔符作为 Field 间的分隔而不是定长 (虽然也并非完全如此)

本文章介绍顺序是先介绍其存储用的数据结构, 分别按其概念模型(包含了什么信息, 为什么要这样设计)及其二进制格式(储存在文件系统中的格式)来介绍; 随后再描述如何实现 Git 的常用功能. 

## `.git` 目录结构

Git 将目录分为三个区:

- 工作目录 (working directory): 即目录中除了 `.git` 目录之外的所有文件, 也就是我们平时写代码的地方
- 暂存区 (index or staging area): 就是平时 add 完文件之后改动暂存的地方, 在 `.git/index` 下. 这里的改动会在下一次 commit 的时候被加入到 repo 里
- Git 仓库 (Git Repository): 存放 git 的所有信息的地方, 也就是 `.git` 目录

### Git Repository

```bash
$ tree .git
.git
├── branches         # 
├── COMMIT_EDITMSG   # 最近 Commit 时打的 Commit Message. 提供这个文件主要是为了与各种 editor 交互
├── config           # 配置文件
├── description      # 仓库描述文件
├── HEAD             # 当前
├── hooks            # 
├── index            # 暂存区文件
├── info             # 
│   └── exclude
├── logs             # 日志
│   ├── HEAD
│   └── refs
│       └── heads
│           └── master
├── objects         # 对象数据库
│   ├── 7e
│   │   └── f4c762de36ab4569c8f8bd0be86c871e68cbc9
│   ├── info
│   └── pack        # 压缩
└── refs            # 引用
    ├── heads
    │   └── master
    └── tags
```

其中`config`文件是一个语法类似[INI文件]()的配置文件, 例子:

```ini
[core]
    # 仓库格式版本(似乎一直是0就没变过)
	repositoryformatversion = 0
    # 是否记录文件权限
	filemode = false
    # 是否允许没有 workpath 
	bare = false
	logallrefupdates = true
	# 文件系统是否支持 符号链接
    symlinks = false
    # 是否忽略大小写
	ignorecase = true
```

## Python 相对路径 import

> 不知道查了多少次了 :( 

一句话: 用相对路径 import 的文件就不要运行. 要运行的文件就不要用相对路径. 

可以将用相对路径的文件`xxx.py`放进包里, 然后在包外`run_xxx.py`内使用包名引用. 此时必须使用`python -m run_xxx.py`.

## Git Object: Git 的数据存储模型

### 一些命令行工具

根据[SO上的一个回答](https://stackoverflow.com/a/28753259), 在 Bash 中定义以下函数:
```bash
zlipd() (printf "\x1f\x8b\x08\x00\x00\x00\x00\x00" |cat - $@ |gzip -dc 2> /dev/null)
```

> 原理大概就是: 
> - gzip 格式其实就是 头部信息 + zlib算法压缩的文件内容
> - 我们往 zlib算法压缩的文件内容 前补上 gzip 的头部信息, 再把它给 gzip 解压, 就能拿到数据

可以方便地查看以`zlib`压缩的文件. 

例子: 
```bash
$ zlipd() (printf "\x1f\x8b\x08\x00\x00\x00\x00\x00" |cat - $@ |gzip -dc 2> /dev/null) # 定义函数
$ zlipd objects/81/c545efebe5f57d4cab2ba9ec294c4b0cadf672
blob 51234

```

如果你清楚 Object 文件的格式的话, 你也可以使用`git cat-file <Object类型> <SHA-1>`命令来直接查看 Object 文件的 data 区而忽略信息头: 

```bash
$ zlipd .git/objects/fe/7ce18c5d359042f6eb43e81cf7119240dd3681| xxd
00000000: 7472 6565 2033 3300 3130 3036 3434 2063  tree 33.100644 c
00000010: 2e74 7874 009c 9ddc 2cc3 6ec5 8f5f c76c  .txt....,.n.._.l
00000020: 7c51 57cf c046 dd79 ea                   |QW..F.y.

$ git cat-file tree fe7c | xxd
00000000: 3130 3036 3434 2063 2e74 7874 009c 9ddc  100644 c.txt....
00000010: 2cc3 6ec5 8f5f c76c 7c51 57cf c046 dd79  ,.n.._.l|QW..F.y
00000020: ea                                       .
```

当然你也可以这样用, 让 Git 帮你查看文件类型(`git cat-file -t <SHA-1>`返回 Object 类型): 

```bash
$ cat-obj() (git cat-file $(git cat-file -t $@) $@)
$ cat-obj fe7c | xxd
00000000: 3130 3036 3434 2063 2e74 7874 009c 9ddc  100644 c.txt....
00000010: 2cc3 6ec5 8f5f c76c 7c51 57cf c046 dd79  ,.n.._.l|QW..F.y
00000020: ea                                       .
```

为了按字节查看内容, 我们可以使用`xxd`: 
```bash
$ zlipd objects/81/c545efebe5f57d4cab2ba9ec294c4b0cadf672 | xxd
00000000: 626c 6f62 2035 0031 3233 340a            blob 5.1234.
```

一般的, 右边预览的`.`可能表示: 

- 点本身
- 空格或换行等不可打印/不好打印的字符

另外可以试试下面的命令: 

```bash
$ zlipd .git/objects/fe/7ce18c5d359042f6eb43e81cf7119240dd3681 | xxd -g 1 | cut -d ' ' -f2-18 | sed 's/ /\\x/g' 
74\x72\x65\x65\x20\x33\x33\x00\x31\x30\x30\x36\x34\x34\x20\x63\x
2e\x74\x78\x74\x00\x9c\x9d\xdc\x2c\xc3\x6e\xc5\x8f\x5f\xc7\x6c\x
7c\x51\x57\xcf\xc0\x46\xdd\x79\xea\x\x\x\x\x\x\x\x
```

- `xxd -g 1`表示1个八位bit一节地输出(也就是两位hex)
- `cut -d ' ' -f2-18`将每行输入按空格分隔后取2到18列
- `sed 's/ /\\x/g'`将输入中每个空格换成`\x`

这样获得的输出可以轻易地在别的文本编辑器中将其转换成 Python 的 bytes. 

```bash
$ find .git/objects -type f 
.git/objects/80/4d54e8fc16d18edccd6a8469e6584800e2c936
.git/objects/0e/f6a7016afc43d518cef9786c8c6075564f32fb
.git/objects/81/c545efebe5f57d4cab2ba9ec294c4b0cadf672
.git/objects/9c/9ddc2cc36ec58f5fc76c7c5157cfc046dd79ea
.git/objects/fe/7ce18c5d359042f6eb43e81cf7119240dd3681
.git/objects/05/e7801182a544c4abbf92588d3d2ab04391ef15
.git/objects/7e/f4c762de36ab4569c8f8bd0be86c871e68cbc9
```

获得目录下所有文件的名字. 

### Object 文件

#### 概念模型

一个`Object 文件`是指存放在`.git/objects`目录下的文件, 它们都是一种压缩文件, 以自己未压缩前的 SHA-1 作为路径存放在该目录下. `Object 文件`中记录了:

- Object 类型: blob/tree/commit/tag
- Object 数据的大小
- Object 数据

前两项是泛用的文件头, 而对不同类型的 Object 它们又有不同种类的数据以不同二进制格式存放于 Object 数据这一区中. 

示意图: 

**TODO**

本文(及代码中)约定: 

- raw: 指未压缩的整个文件内容
- sha: 指未压缩的整个文件内容的 SHA-1, 即 `sha1(raw)`
- data: 指 Object 数据

下文中分对象类型介绍时一般仅仅介绍 Object 数据的概念/存放格式, 而省略前面的几个通用的数据头. 

#### 二进制格式

从文件开头开始: 

- 一个标识类型的 ASCII 字符串: 为 `blob`, `tree`, `commit`, `tag` 其中之一
- 一个分隔用的 ASCII 空格
- Object 数据压缩前的大小, 以 byte 为单位, 写成数字后以 ASCII 字符串格式存起来
- 一个分隔用的 NUL 字符
- Object 数据 

然后再一起用[zlib]()压缩之后存到对应的文件中. 代码如下: 

```python
# Blob 类型文件的储存方法, 作为例子
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
```


### Blob 对象

#### 概念模型

Blob: Binary Large OBject, 二进制大型对象的缩写. 

其实就是一个简单的放文件内容的容器. 

#### 二进制格式

简简单单, `data`区里放的就是数据. 

```python
class Blob(GitObject):
    obj_type: Final[GitObjectType] = b'blob'

    def deserialize(self, data: bytes) -> None:
        self.data = data

    def serialize(self) -> bytes:
        return self.data
```

### Commit 对象


#### 概念模型:  Kvlm/Key-Value List with Message

Commit Object 的 data 部分就是简简单单的一个 kvlm.

> 建立 kvlm 概念的原因是因为 Commit 与 Tag 共享这个结构

kvlm 其实就是**一个有序键值对列表 + 一条信息**. 比如:  

```bash
$ git cat-file -p 804d
tree 7ef4c762de36ab4569c8f8bd0be86c871e68cbc9
author Origami404 <Origami404@foxmail.com> 1613116353 +0800
committer Origami404 <Origami404@foxmail.com> 1613116353 +0800

Commit Message

```

键值对列表: 

1. tree      : 7ef4c762de36ab4569c8f8bd0be86c871e68cbc9
2. author    : Origami404 <Origami404@foxmail.com> 1613116353 +0800
3. committer : Origami404 <Origami404@foxmail.com> 1613116353 +0800

信息: 

```
Commit Message
```

一般来讲, 一个 Commit 对象大概会有下面这些信息: 

- `tree`: 它对应的文件树
- `parent`: 它的父 Commit 对象, 第一个 Commit 没有这个 field
- `author`: 作者
- `committer`: 提交者

#### 二进制格式

`data`区里放的是一个`kvlm`. 

下面定义`kvlm`:

```
kvlm    ::= <kv_list>\n<message>

value   ::= <line>[(\n<line>)*]
line    ::= <可打印非回车 ASCII 字符>

kv_list ::= <key> <value>
key     ::= [0-9a-zA-Z]
value   ::= block

message ::= block
```

简要描述: 

- 文件被一个空行分为两部分: <kv-list> 与 <message>.
- <kv-list> 部分基本上一行一个 key-value 对, 以空格分隔 key 和 value. 
- value 里可能有空格, 它也有可能是多行的. 这种情况下下一行开头会是一个空格表示自己是上一行的一部分. 这个空格不算在 value 里.
- <message> 的情况基本上和 value 类似. 

例子/单元测试: (注意 python 多行字符串对回车的处理: Message后有一个回车)

```python
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

```

具体代码: 

```python
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

```

#### Wait, does that make Git a blockchain?

轻松一下. 

摘自[Write yourself a git](https://wyag.thb.lt/#orgea3fb85):

> Wait, does that make Git a blockchain?
>
> Because of cryptocurrencies, blockchains are all the hype these days. And yes, in a way, Git is a blockchain: it’s a sequence of blocks (commits) tied together by cryptographic means in a way that guarantee that each single element is associated to the whole history of the structure. Don’t take the comparison too seriously, though: we don’t need a GitCoin. Really, we don’t.

翻译: 

> 等等, Commit Object 是不是把 Git 变成了一个区块链?
>
> 因为加密货币的缘故, 区块链如今已被大肆吹捧了. 确实, 在某种层面上, Git 确实是一个区块链: 它是一系列的区块(Commit Object)通过某种密码学方法绑定起来, 并且这种方法保证每一个区块都与其全部历史联系起来. 但不要太认真了: 我们真的不需要某种"吉特币(GitCoin)", 真的. 

### Tree 对象

#### 概念模型

Tree Object 储存了文件在文件系统里的结构. 每个 Commit Object 都有一个表示 work_path 的 tree-sha1 键值对. 

具体映射: 

- 目录 -> Tree Object
- 文件 -> Blob Object

如图: 

**TODO**

一个 Tree Object 包含的信息可以**抽象化描述为 (权限模式, 名字, SHA-1) 三元组的列表**

举个例子: 

```bash
$ tree .
.
├── a.txt
└── b
    └── c.txt

1 directory, 2 files
```

然后把整个工作目录 Commit 上去, 那么我们就会有: 

- 两个 Blob 对象分别存放 `a.txt` 与 `b.txt` 的内容 
- 两个 Tree 对象分别存放 `.` 与 `./b` 目录的内容
- 一个 Commit 对象保存着现在 `.` 那个 Tree 对象的 SHA-1

```bash
$ git cat-file -p fe7c
100644 blob 9c9ddc2cc36ec58f5fc76c7c5157cfc046dd79ea    c.txt

$ git cat-file -p 05e7
100644 blob 81c545efebe5f57d4cab2ba9ec294c4b0cadf672    a.txt
040000 tree fe7ce18c5d359042f6eb43e81cf7119240dd3681    b
```

对于保存着 `.` 的那个 Tree 对象来讲: 

| 权限模式 | 名字  |                  SHA-1                   |
| :------: | :---: | :--------------------------------------: |
|  100644  | a.txt | 81c545efebe5f57d4cab2ba9ec294c4b0cadf672 |
|  040000  |   b   | fe7ce18c5d359042f6eb43e81cf7119240dd3681 |

对于保存着 `./b` 那个 Tree对象来讲: 

| 权限模式 | 名字  |                  SHA-1                   |
| :------: | :---: | :--------------------------------------: |
|  100644  | c.txt | 9c9ddc2cc36ec58f5fc76c7c5157cfc046dd79ea |


#### 二进制格式 

Tree 的`data`由一堆有序的无分隔符的条目组成.

其中每一个条目包含: 

- `mode`: 描述文件权限的 **5位或6位** ASCII 数字
- 分隔用空格
- `name`: 文件的名字, 字节序列跟文件系统里的相同
- 分隔用 NUL
- `sha1_raw`: 以二进制格式存储的 SHA-1 值

> 下面的文件有的专门指文件, 有的包括了文件/文件夹/设备 or whatever, 读者应该可以根据常识区分. 

`mode` 其实是 UNIX 文件系统里 modes 的一个小子集. 具体来讲我只找到这几种:

1. `100644`: 普通文件
2. `100664`: 普通文件, 但同组用户可写
3. `100755`: 可执行文件
4. `120000`: 符号链接 (Symbolic Link)
5. `040000`: 目录  (储存为`40000`, 不存第一位的0)
6. `160000`: 子模块

> 134 来自 [Git Internals](https://git-scm.com/book/en/v2/Git-Internals-Git-Objects#_tree_objects)
> 
> 56 来自SO: [https://stackoverflow.com/questions/54596206/what-are-the-possible-modes-for-entries-in-a-git-tree-object]
> 
> 2  来自SO: [https://stackoverflow.com/a/8347325]

> 对于泛用的 UNIX mode [这里](https://stackoverflow.com/a/737877)有一点解释. 
> 简单来说前两位表示文件类型, 第三位是 "set-uid/set-gid/sticky bits", 表示可执行文件运行时的权限([参考](https://www.geeksforgeeks.org/setuid-setgid-and-sticky-bits-in-linux-file-permissions/)); 后三位就是普通的 Unix 权限 mode. 

`name` 就是文件的名字. 文件在文件系统里的名字存的什么字节序列就是什么.

`sha1_raw` 是将 SHA-1 的数值 **依大端序存为 20 bit 的 unsigned int** 后的字节序列.  

具体到实现上就是这样: 

```python
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
        # 大端序
        sha1_int = int.from_bytes(self.sha1_raw, 'big')
        # 去除前导的 0x
        return hex(sha1_int)[2:]


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
```

### Tag Object

Git 中的 Tag 有两种: 

- 轻量级 Tag (Lightweight Tags): 就是普通的对某对象的引用. 
- 标注的 Tag (Annotated Tags): 对一个储存了一些元信息的对象(Tag Object)的引用. 

> 关于引用请[参看下文]()

本节所描述的 Tag Object 指的自然就是那个储存着元信息的对象. 

#### 概念模型

高度类似 Commit Object. 有时候你会想知道到底是谁在什么时候打的某个 Tag. 这时候你就要创建一个 Tag Object 把这些信息写进去, 然后创建一个 Annotated Tag 让它指向这个 Tag Object.

#### 二进制格式

就是一个 Kvlm.

```python
class Tag(GitObject):
    obj_type: Final[GitObjectType] = b'tag'
    
    def deserialize(self, data: bytes) -> None:
        self.dct, self.msg = parse_kvlm(data)

    def serialize(self) -> bytes:
        return unparse_kvlm(self.dct, self.msg)
```

### 一个概览的例子

我们创建一个作为例子的小仓库来查看 Git 的具体格式. 

```bash
$ git --version
git version 2.30.1
```

```bash
$ git init
$ echo '1234' > a.txt
$ git add a.txt
$ git commit -m "Commit Message"
```

```bash
$ tree -a .
.
├── a.txt
└── .git
    ├── branches
    ├── COMMIT_EDITMSG
    ├── config
    ├── description
    ├── HEAD
    ├── hooks
    │   ├── applypatch-msg.sample
    │   ├── commit-msg.sample
    │   ├── fsmonitor-watchman.sample
    │   ├── post-update.sample
    │   ├── pre-applypatch.sample
    │   ├── pre-commit.sample
    │   ├── pre-merge-commit.sample
    │   ├── prepare-commit-msg.sample
    │   ├── pre-push.sample
    │   ├── pre-rebase.sample
    │   ├── pre-receive.sample
    │   ├── push-to-checkout.sample
    │   └── update.sample
    ├── index
    ├── info
    │   └── exclude
    ├── logs
    │   ├── HEAD
    │   └── refs
    │       └── heads
    │           └── master
    ├── objects
    │   ├── 7e
    │   │   └── f4c762de36ab4569c8f8bd0be86c871e68cbc9
    │   ├── 80
    │   │   └── 4d54e8fc16d18edccd6a8469e6584800e2c936
    │   ├── 81
    │   │   └── c545efebe5f57d4cab2ba9ec294c4b0cadf672
    │   ├── info
    │   └── pack
    └── refs
        ├── heads
        │   └── master
        └── tags

16 directories, 26 files

$ git cat-file -t 81c5
blob

$ git cat-file -t 7ef4
tree

$ git cat-file -t 804d
commit

```

#### Blob Object

```bash
$ zlipd .git/objects/81/c545efebe5f57d4cab2ba9ec294c4b0cadf672      
blob 51234

$ zlipd .git/objects/81/c545efebe5f57d4cab2ba9ec294c4b0cadf672 | xxd
00000000: 626c 6f62 2035 0031 3233 340a            blob 5.1234.
```

#### Commit Object

```bash
$ zlipd .git/objects/80/4d54e8fc16d18edccd6a8469e6584800e2c936 
commit 185tree 7ef4c762de36ab4569c8f8bd0be86c871e68cbc9
author Origami404 <Origami404@foxmail.com> 1613116353 +0800
committer Origami404 <Origami404@foxmail.com> 1613116353 +0800

Commit Message

$ zlipd .git/objects/80/4d54e8fc16d18edccd6a8469e6584800e2c936 | xxd
00000000: 636f 6d6d 6974 2031 3835 0074 7265 6520  commit 185.tree 
00000010: 3765 6634 6337 3632 6465 3336 6162 3435  7ef4c762de36ab45
00000020: 3639 6338 6638 6264 3062 6538 3663 3837  69c8f8bd0be86c87
00000030: 3165 3638 6362 6339 0a61 7574 686f 7220  1e68cbc9.author 
00000040: 4f72 6967 616d 6934 3034 203c 4f72 6967  Origami404 <Orig
00000050: 616d 6934 3034 4066 6f78 6d61 696c 2e63  ami404@foxmail.c
00000060: 6f6d 3e20 3136 3133 3131 3633 3533 202b  om> 1613116353 +
00000070: 3038 3030 0a63 6f6d 6d69 7474 6572 204f  0800.committer O
00000080: 7269 6761 6d69 3430 3420 3c4f 7269 6761  rigami404 <Origa
00000090: 6d69 3430 3440 666f 786d 6169 6c2e 636f  mi404@foxmail.co
000000a0: 6d3e 2031 3631 3331 3136 3335 3320 2b30  m> 1613116353 +0
000000b0: 3830 300a 0a43 6f6d 6d69 7420 4d65 7373  800..Commit Mess
000000c0: 6167 650a                                age.
```

#### Tree Object

```bash
$ zlipd .git/objects/7e/f4c762de36ab4569c8f8bd0be86c871e68cbc9 | xxd 
00000000: 7472 6565 2033 3300 3130 3036 3434 2061  tree 33.100644 a
00000010: 2e74 7874 0081 c545 efeb e5f5 7d4c ab2b  .txt...E....}L.+
00000020: a9ec 294c 4b0c adf6 72                   ..)LK...r
```

## Git Index: Git 的暂存区

- 每一次的 add 都

### 二进制格式

前后顺序**均按从低位到高位**. 

```
<index>     ::= <header/12-byte> <entries/8k-byte> <extensions> <checksum>

<header>    ::= <signature/4-byte> <version/4-byte> <entry_cnt/32-bit>
<signature> ::= b'DIRC' 
<version>   ::= (0002, 0003, 0004)                          in ASCII format
<entry_cnt> ::= the amount of entries below                 in u32   format

<entries>   ::= [<entry> <padding>]
<entry>     ::= <c_time/32-bit> <c_time_ns/32-bit>
                <m_time/32-bit> <m_time_ns/32-bit>
                <dev/32-bit>    <ino/32-bit>
                <mode/32-bit>
                <uid/32-bit>    <gid/32-bit>
                <file_size/32-bit>
                <sha-1/20-byte>
                <flags/16-bit>
                <path_name>

<c_time>    ::= 以秒为单位的最后一次文件元信息改变时间      in u32 format
<c_time_ns> ::= c_time 的纳秒部分                           in u32 format

<m_time>    ::= 以秒为单位的最后一次文件改变时间            in u32 format
<m_time_ns> ::= m_time 的纳秒部分                           in u32 format

<dev>       ::= 文件的设备号
<ino>       ::= 文件的 ino (Infomation NOde) 号,            in u32 format
                与 <dev> 一起在能同一台机器上唯一地确定某个文件

<mode>      ::= <unused_0/16-bit> <obj_type/4-bit> <unused_0/3-bit> <unix-permission/9-bit>
<obj_type>  ::= (1000, 1010, 1110) 三选一 
                分别代表文件类型为 (普通文件, 符号链接, 子模块链接(Gitlink))
<unix-permission> ::= 常见的 Unix 权限位, 就是 644 / 777 那种

<uid>       ::= 文件所有者的用户 ID                         in u32 format
<gid>       ::= 文件所有者的用户组 ID                       in u32 format

<file_size> ::= 文件的大小, 按字节记                        in u32 format
<sha-1>     ::= 对象的 SHA-1                                in u160 format (20-byte 长的二进制数)

<flags>     ::= <assume-valid/1-bit> <extended/1-bit> <stage/2-bit> <path_len/12-bit>
<assume-vaild> ::= Flag, 为 1 时 Git 会假定此文件未变动, 从而允许你让 Git 忽略该文件的改变
<extended>  ::= Flag, 在 version 2 中一定为 0
<stage>     ::= 描述其属于同路径名对象的哪个 Slot
<path_len>  ::= 路径名长度, 如果大于等于 0xFFF(4095) 的话就是 0xFFF

<path_name> ::= 路径名, 统一用 "/" 作为路径分隔符
```

直接按以上二进制格式储存于 `.git/index` 文件中, 不需要压缩

### 一个例子

现在我们的工作目录里有两个文件: `a.txt` 与 `b/c.txt`.

```bash
$ tree .
├─b
│ └─c.txt
└─a.txt
```

```bash
$ cat .git/index | xxd
00000000: 4449 5243 0000 0002 0000 0002 6026 33b5  DIRC........`&3.
00000010: 053f fd99 6026 33b5 053f fd99 0000 0802  .?..`&3..?......
00000020: 0050 008b 0000 81a4 0000 03e8 0000 03e8  .P..............
00000030: 0000 0005 81c5 45ef ebe5 f57d 4cab 2ba9  ......E....}L.+.
00000040: ec29 4c4b 0cad f672 0005 612e 7478 7400  .)LK...r..a.txt.
00000050: 0000 0000 6026 6662 15c4 8f97 6026 6662  ....`&fb....`&fb
00000060: 15c4 8f97 0000 0802 0056 0b99 0000 81a4  .........V......
00000070: 0000 03e8 0000 03e8 0000 0005 9c9d dc2c  ...............,
00000080: c36e c58f 5fc7 6c7c 5157 cfc0 46dd 79ea  .n.._.l|QW..F.y.
00000090: 0007 622f 632e 7478 7400 0000 5452 4545  ..b/c.txt...TREE
000000a0: 0000 0033 0032 2031 0a05 e780 1182 a544  ...3.2 1.......D
000000b0: c4ab bf92 588d 3d2a b043 91ef 1562 0031  ....X.=*.C...b.1
000000c0: 2030 0afe 7ce1 8c5d 3590 42f6 eb43 e81c   0..|..]5.B..C..
000000d0: f711 9240 dd36 8137 fd86 0a4c e3d2 cdd2  ...@.6.7...L....
000000e0: c822 c701 1d2f dc6e 5c97 68              .".../.n\.h
```

我们把它按上文的字段分开一个一个看: 

```bash
# 文件头
4449 5243 0000 0002 0000 0002 

# 第一个条目
6026 33b5 053f fd99 6026 
33b5 053f fd99 0000 0802  
0050 008b 0000 81a4 0000 
03e8 0000 03e8 0000 0005 
81c5 45ef ebe5 f57d 4cab 
2ba9 ec29 4c4b 0cad f672 
0005 612e 7478 7400 0000 0000 

# 第二个条目
6026 6662 15c4 8f97 
6026 6662 15c4 8f97 0000 
0802 0056 0b99 0000 81a4  
0000 03e8 0000 03e8 0000 
0005 9c9d dc2c c36e c58f 
5fc7 6c7c 5157 cfc0 46dd 
79ea 0007 622f 632e 7478 
7400 0000            

# 扩展 & Hash checksum
5452 4545  
0000 0033 0032 2031 0a05 e780 1182 a544  
c4ab bf92 588d 3d2a b043 91ef 1562 0031  
2030 0afe 7ce1 8c5d 3590 42f6 eb43 e81c  
f711 9240 dd36 8137 fd86 0a4c e3d2 cdd2  
c822 c701 1d2f dc6e 5c97 68              

# ---------- 下面是详细解释 -----------------

# 文件头
4449 5243  # 4-byte signature: DIRC
0000 0002  # 4-byte ASCII version: 2
0000 0002  # 32-bit entry count: 2

# 条目 1: a.txt
6026 33b5  # 32-bit: c_time
053f fd99  # 32-bit: c_time_ns
6026 33b5  # 32-bit: m_time
053f fd99  # 32-bit: m_time_ns

0000 0802  # 32-bit: dev
0050 008b  # 32-bit: ino

0000 81a4  # 32-bit: mode: 4-bit obj_type / 3-bit unused / 9-bit unix permission
           # 81a4: 1000 000 110100100 : 1000 for file, 000 for unused, 110/100/100 for mode 644

0000 03e8  # 32-bit: uid
0000 03e8  # 32-bit: gid

0000 0005  # 32-bit: size of the file from stat(2), means len('1234\n') == 5

81c5 45ef ebe5 f57d 4cab # 20-byte: the SHA-1 of the object in a SHA-1 repo
2ba9 ec29 4c4b 0cad f672 # 

0005 # flags: 1-bit / 1-bit / 2-bit / 12-bit size of its path name below: 5

612e 7478 74  # its path name: 'a.txt'
00 0000 0000  # padding: 让每一个条目的大小是 8-byte 的倍数, 并且保证至少有一个 NUL (size: 72 bytes)

# 条目 2: b/c.txt
# 相信读者可以自行解读下面的字段了
6026 6662 
15c4 8f97 
6026 6662 
15c4 8f97 

0000 0802 
0056 0b99 

0000 81a4  

0000 03e8 
0000 03e8 

0000 0005 

9c9d dc2c c36e c58f 5fc7 
6c7c 5157 cfc0 46dd 79ea 

0007 

622f 632e 7478 74  # b/c.txt
00 0000            

# 扩展 & Hash checksum: 略
```

### Stage 字段的含义

在 Git 合并分支的时候有用. 

例子取自参考里的 SO 问题. 

假如我们现在有两个分支 `A`, `B`, 工作目录下原本有三个文件 `x`, `y`, `z`. 现在你: 

在 `A` 分支:
 
- 修改了 `x` 的内容并且将它的名字改成了 `t`
- 修改了 `y` 的内容
- `z` 的内容保持不变

在 `B` 分支: 

- 修改了 `x` 的内容
- 删除了 `y`
- `z` 的内容保持不变

这时候你在 `A` 分支, 想要把它合并到 `B` 分支: 

```bash
(on git:A)$ git merge B
```

这时候 Git 就会要求你手动合并冲突, 此时的 `index` 文件内容如下:

```bash
(on git:A)$ git ls-file --stage
100644  4362ab...   1   t   # 指向保存了原来的 x 文件内容的 blob
100644  49db92...   2   t   # 指向保存了 当前分支A 中 t(原来的x) 文件内容的 blob
100644  04b399...   3   t   # 指向保存了 要被合并分支B 中 x 文件内容的 blob
100644  366b52...   1   y   # 指向保存了原来的 y 文件内容的 blob
100644  6fecb1...   2   y   # 指向保存了 当前分支A 中 y 文件
                            # 因为在 B 分支中 y 被删除了, 所以没有 stage 为 3 的 B分支 y 文件 blob
100644  7129c6...   0   z   # 没有冲突的正常文件 stage 号为 0
```

当你解决完冲突合并之后, 比如说你:

- 选择了 `t` 文件
- 删除了 `y` 文件

那么合并成功后 `index` 会变成这样: 

```bash
(on git:B)$ git ls-file --stage
100644  49db92...   0   t
100644  7129c6...   0   z
```

> 参考: 
>
> 二进制格式: [Git Manuel](https://git-scm.com/docs/index-format). 请特别注意它的排版方式, 可以的话建议先看完前文再去看这个
> 
> Stat 字段的意义: [Python os.stat](https://docs.python.org/zh-cn/3.8/library/os.html#os.stat_result)
>
> Assume-vaild flag 的意义: [SO-1: 描述了 Assume-vaild flag 对应的 Git 高层术语](https://stackoverflow.com/questions/47263883/eclipse-git-what-is-assume-valid), [SO-2: 描述了该高层术语的一种应用场景](https://stackoverflow.com/questions/16779929/how-do-i-make-to-some-of-the-files-that-i-have-changed-is-not-offered-in-the-com),  [Git Manuel: 描述了如何设置这一 Flag](https://git-scm.com/docs/git-update-index#Documentation/git-update-index.txt---no-assume-unchanged)
>
> Stage/2-bit 的含义参考: [描述了其对应的高层术语 Slot](https://mincong.io/2018/04/28/git-index/#1-understand-index-via-git-ls-files), [SO: 解释了其用途](https://stackoverflow.com/questions/21309490/how-do-contents-of-git-index-evolve-during-a-merge-and-whats-in-the-index-afte)
>
> 实现参考: [Dulwich index.py](https://github.com/dulwich/dulwich/blob/2cf84bf9ca358655849761d81d1fe2b96e8952ed/dulwich/index.py), [Gin](https://github.com/sbp/gin/blob/master/gin)


## Git Command: Git 的数据使用方式

现在让我们来使用上面我们写好的 Git Object 来实现常用的 Git 命令吧. 

### Spec

我们要实现的命令有这些: 

#### 创建仓库: 

```bash
$ git init [path]
# [path]: 在 [path] 下创建一个包含必要目录结构的 .git 目录, 默认为 . (当前目录)
```

#### 泛用 Object 文件 IO

提供 `data` 写入 Object 文件的命令: 

```bash
$ git hash-object [-t <type>] [-w] (<file> | --stdin)
# [-t <type>] : Object 类型, 默认为 Blob
# [-w] : 是否真正写入 .git/objects 数据库, 默认为否
# <file>: Data 的来源文件. 文件内容会被当成 data
# --stdin: 从标准输入获取, 一行一个 Object
# 输出是 Data 打包成 Raw 后的 SHA-1, 如: 
ebf4a6068f1c4176bf8db06771445b4d994f2199
```

从 Object 文件里读取 `data` 并将其有效信息显示出来的命令

```bash
$ git cat-file (-t | -s | -p | <type>) <object>
# -t: 输出 Object 文件的类型
# -s: 输出 Object 文件的大小 (按字节计)
# -p: 按照文件中指示的类型美观地输出 data
# <type>: 按照类型输出 data 的原始内容
# <object>: 可以唯一确定某个 Object 的指示符, 具体见下文
```

#### 暂存区 & Tree Object


