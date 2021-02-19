# Git Object: Git 的数据存储模型

## 一些命令行工具

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

## Object 文件

### 概念模型

一个`Object 文件`是指存放在`.git/objects`目录下的文件, 它们都是一种压缩文件, 以自己未压缩前的 SHA-1 作为路径存放在该目录下. `Object 文件`中记录了:

- Object 类型: blob/tree/commit/tag
- Object 数据的大小
- Object 数据

前两项是泛用的文件头, 而对不同类型的 Object 它们又有不同种类的数据以不同二进制格式存放于 Object 数据这一区中. 

示意图: 

![Object File](ObjectFile.svg)

本文(及代码中)约定: 

- raw: 指未压缩的整个文件内容
- sha: 指未压缩的整个文件内容的 SHA-1, 即 `sha1(raw)`
- data: 指 Object 数据

下文中分对象类型介绍时一般仅仅介绍 Object 数据的概念/存放格式, 而省略前面的几个通用的数据头. 

### 二进制格式

从文件开头开始: 

- 一个标识类型的 ASCII 字符串: 为 `blob`, `tree`, `commit`, `tag` 其中之一
- 一个分隔用的 ASCII 空格
- Object 数据压缩前的大小, 以 byte 为单位, 写成数字后以 ASCII 字符串格式存起来
- 一个分隔用的 NUL 字符
- Object 数据 

然后再一起用[zlib](https://zlib.net/)压缩之后存到对应的文件中. 代码如下: 

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


## Blob 对象

### 概念模型

Blob: Binary Large OBject, 二进制大型对象的缩写. 

其实就是一个简单的放文件内容的容器. 

### 二进制格式

简简单单, `data`区里放的就是数据. 

```python
class Blob(GitObject):
    obj_type: Final[GitObjectType] = b'blob'

    def deserialize(self, data: bytes) -> None:
        self.data = data

    def serialize(self) -> bytes:
        return self.data
```

## Commit 对象


### 概念模型:  Kvlm/Key-Value List with Message

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

### 二进制格式

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

### Wait, does that make Git a blockchain?

轻松一下. 

摘自[Write yourself a git](https://wyag.thb.lt/#orgea3fb85):

> Wait, does that make Git a blockchain?
>
> Because of cryptocurrencies, blockchains are all the hype these days. And yes, in a way, Git is a blockchain: it’s a sequence of blocks (commits) tied together by cryptographic means in a way that guarantee that each single element is associated to the whole history of the structure. Don’t take the comparison too seriously, though: we don’t need a GitCoin. Really, we don’t.

翻译: 

> 等等, Commit Object 是不是把 Git 变成了一个区块链?
>
> 因为加密货币的缘故, 区块链如今已被大肆吹捧了. 确实, 在某种层面上, Git 确实是一个区块链: 它是一系列的区块(Commit Object)通过某种密码学方法绑定起来, 并且这种方法保证每一个区块都与其全部历史联系起来. 但不要太认真了: 我们真的不需要某种"吉特币(GitCoin)", 真的. 

## Tree 对象

### 概念模型

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


### 二进制格式 

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

## Tag Object

Git 中的 Tag 有两种: 

- 轻量级 Tag (Lightweight Tags): 就是普通的对某对象的引用. 
- 标注的 Tag (Annotated Tags): 对一个储存了一些元信息的对象(Tag Object)的引用. 

> 关于引用请[参看下文]()

本节所描述的 Tag Object 指的自然就是那个储存着元信息的对象. 

### 概念模型

高度类似 Commit Object. 有时候你会想知道到底是谁在什么时候打的某个 Tag. 这时候你就要创建一个 Tag Object 把这些信息写进去, 然后创建一个 Annotated Tag 让它指向这个 Tag Object.

### 二进制格式

就是一个 Kvlm.

```python
class Tag(GitObject):
    obj_type: Final[GitObjectType] = b'tag'
    
    def deserialize(self, data: bytes) -> None:
        self.dct, self.msg = parse_kvlm(data)

    def serialize(self) -> bytes:
        return unparse_kvlm(self.dct, self.msg)
```

## 一个概览的例子

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

### Blob Object

```bash
$ zlipd .git/objects/81/c545efebe5f57d4cab2ba9ec294c4b0cadf672      
blob 51234

$ zlipd .git/objects/81/c545efebe5f57d4cab2ba9ec294c4b0cadf672 | xxd
00000000: 626c 6f62 2035 0031 3233 340a            blob 5.1234.
```

### Commit Object

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

### Tree Object

```bash
$ zlipd .git/objects/7e/f4c762de36ab4569c8f8bd0be86c871e68cbc9 | xxd 
00000000: 7472 6565 2033 3300 3130 3036 3434 2061  tree 33.100644 a
00000010: 2e74 7874 0081 c545 efeb e5f5 7d4c ab2b  .txt...E....}L.+
00000020: a9ec 294c 4b0c adf6 72                   ..)LK...r
```
