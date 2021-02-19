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

本文章不是 Git 的教程, 如果读者对 Git 的操作并非十分了解的话可以参考 ProGit, 一本非常好的 Git 教材. 

~~或者也可以像我一样现学现写~~

灵感来源: [Write Yourself a Git](https://wyag.thb.lt/), [深入理解Git实现原理](https://zhuanlan.zhihu.com/p/45510461), 同时大量参考了杂七杂八的文章. 

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