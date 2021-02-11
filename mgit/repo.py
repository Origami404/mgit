import os
from configparser import ConfigParser
from typing import Final


class GitRepo:
    """A git repository"""
    def __init__(self, work_path: str):
        self.work_path = work_path
        self.gitdir = os.path.join(work_path, '.git')
        self.conf = ConfigParser()

    def _ensure_exist(self, dir_path: str, create: bool = True) -> None:
        '''确保目录路径存在
        @parma create: 若为 True 则在目录不存在时创造, 否则报错
        '''

        if os.path.exists(dir_path):
            # 路径存在但不为目录: 报错
            if not os.path.isdir(dir_path):
                raise RuntimeError(f"Path exist but not a dir: {dir_path}")
            # 路径存在且为目录: pass
        elif not create:
            # 路径不存在且不需要创造: 报错
            raise RuntimeError(f"Path not exist: {dir_path}")
        else:
            # 路径不存在且需要创造: 创造目录
            os.makedirs(dir_path)

    def repo_dir(self, *paths, create: bool = True) -> str:
        """获得相对于 .git 目录下某个目录的绝对路径
        @param create: 当目录不存在时是否创造目录
        """
        dir_path: Final = os.path.join(self.gitdir, *paths)
        self._ensure_exist(dir_path, create)
        return dir_path

    def repo_file(self, *path, create: bool = True) -> str:
        """获得相对于 .git 目录下某个文件的绝对路径
        @param create: 当目录不存在时是否创造目录
        """
        dir_path: Final = self.repo_dir(*path[:-1], create=create)
        return os.path.join(dir_path, path[-1])

    def init_repo(self) -> 'GitRepo':
        # 检验工作目录是否存在
        self._ensure_exist(self.work_path, create=True)

        # 创建基础目录
        self.repo_dir('branches', create=True)  # 保存分支
        self.repo_dir('objects', create=True)  # 保存对象
        self.repo_dir('refs', 'tags', create=True)  # 保存 Tags
        self.repo_dir('refs', 'heads', create=True)  # 保存

        # 创建基础文件

        # 辅助函数
        def open_repo(filename):
            return open(self.repo_file(filename), 'w')

        # 描述文件: description
        with open_repo('description') as f:
            f.write("Unnamed repository; edit this file 'description' to name the repository.\n")
        # 当前分支头部: HEAD
        with open_repo('HEAD') as f:
            f.write('ref: refs/heads/master\n')
        # 配置文件: config
        with open_repo('config') as f:
            config_parser = repo_default_config()
            config_parser.write(f)

        return self

    def load_repo(self, force: bool = False) -> 'GitRepo':
        '''加载一个已经存在的 Git repo 并读取其 Config'''
        if not os.path.isdir(self.gitdir):
            raise RuntimeError(f"Not a git repo: {self.work_path}")

        _Exception = RuntimeWarning if force else RuntimeError
        conf_path = self.repo_file('config')

        if not os.path.exists(conf_path):
            raise _Exception(f'Missing a config file: {self.work_path}')

        self.conf.read(conf_path)

        version = int(self.conf.get('core', 'repositoryformatversion'))
        if version != 0:
            raise _Exception(f'Unsupport version: {version}')

        return self


def repo_default_config() -> ConfigParser:
    ret = ConfigParser()

    ret.add_section("core")

    # Git repo 的格式版本: My Git 0 版本
    ret.set("core", "repositoryformatversion", "0")
    # 是否监控文件权限变化: 否
    ret.set("core", "filemode", "false")
    # 是否没有 worktree: 否
    ret.set("core", "bare", "false")

    return ret


def create_repo(work_path) -> GitRepo:
    return GitRepo(work_path).init_repo()


def load_repo(work_path, force: bool = False) -> GitRepo:
    return GitRepo(work_path).load_repo(force)
