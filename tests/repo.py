import unittest
import os
from mgit.repo import create_repo

test_workpath = r'C:\Users\Administrator\Desktop\LT\mgit\tests\test_workpath'


class TestGitRepo(unittest.TestCase):

    # 初始化一个测试工作目录
    def setUp(self):
        # 确保测试工作目录存在
        if not os.path.exists(test_workpath):
            os.makedirs(test_workpath)

        # 清空测试工作目录
        map(os.remove, os.listdir(test_workpath))

    def test_create_repo(self):
        repo = create_repo(test_workpath)

        def assertDirExist(*rel_path):
            path = repo.repo_dir(*rel_path)
            self.assertTrue(os.path.exists(path))

        assertDirExist('branches')
        assertDirExist('object')
        assertDirExist('refs', 'tags')
        assertDirExist('refs', 'heads')

        def assertFileContent(filename, content):
            with open(repo.repo_file(filename), 'r') as f:
                self.assertEqual(f.read(), content)

        assertFileContent('description', "Unnamed repository; edit this file 'description' to name the repository.\n")
        assertFileContent('HEAD', 'ref: refs/heads/master\n')

        # TODO: 增加 Conf 的判断
