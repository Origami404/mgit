import unittest
import os
from mgit.repo import create_repo
from test_config import test_workpath


class TestGitRepo(unittest.TestCase):

    # 初始化一个测试工作目录
    def setUp(self):
        # 确保测试工作目录存在
        if not os.path.exists(test_workpath):
            os.makedirs(test_workpath)

        # 清空测试工作目录
        os.system(f"rm -rf {os.path.join(test_workpath, '.git')}")

    def test_create_repo(self):
        repo = create_repo(test_workpath)

        def assertDirExist(*rel_path):
            path = repo.repo_dir(*rel_path, create=False)
            self.assertTrue(os.path.exists(path))

        assertDirExist('branches')
        assertDirExist('objects')
        assertDirExist('refs', 'tags')
        assertDirExist('refs', 'heads')

        def assertFileContent(filename, content):
            with open(repo.repo_file(filename), 'r') as f:
                self.assertEqual(f.read(), content)

        assertFileContent('description', "Unnamed repository; edit this file 'description' to name the repository.\n")
        assertFileContent('HEAD', 'ref: refs/heads/master\n')

        # TODO: 增加 Conf 的判断
