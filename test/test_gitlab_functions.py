#!/usr/bin/env python3
"""
GitLab代码功能单元测试
测试目标：验证GitLab代码中零commit ID的处理逻辑
测试过程：
1. 测试get_diff_files函数对零commit ID的处理
2. 测试get_rules函数对零commit ID的处理  
3. 测试get_commit_files函数的基本功能
期望输出：
- 零commit ID时正确调用get_commit_files函数
- 零commit ID时get_rules使用branch作为ref
- 所有测试用例通过
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# 添加lambda目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lambda'))

import gitlab_code
import base


class TestGitLabFunctions(unittest.TestCase):
    """GitLab代码功能测试类"""
    
    def setUp(self):
        """测试前准备：创建mock项目对象"""
        self.mock_project = Mock()
        self.zero_commit = "0000000000000000000000000000000000000000"
        self.normal_commit = "abc123def456"
        self.branch_name = "dev"
    
    def test_zero_commit_handling(self):
        """
        测试零commit ID处理逻辑
        验证当from_commit_id为全零时，get_diff_files调用get_commit_files
        """
        print("\n=== 测试零commit ID处理 ===")
        
        # Mock get_commit_files函数的返回值
        expected_files = {
            'src/main.py': 'diff content for main.py',
            'README.md': 'diff content for README.md'
        }
        
        with patch.object(gitlab_code, 'get_commit_files', return_value=expected_files) as mock_get_commit_files:
            # 调用get_diff_files，使用零commit ID
            result = gitlab_code.get_diff_files(self.mock_project, self.zero_commit, self.normal_commit)
            
            # 验证get_commit_files被调用
            mock_get_commit_files.assert_called_once_with(self.mock_project, self.normal_commit)
            
            # 验证返回结果
            self.assertEqual(result, expected_files)
            print(f"✅ 零commit ID处理正确，返回{len(result)}个文件")
    
    def test_normal_commit_handling(self):
        """
        测试正常commit ID处理逻辑
        验证当from_commit_id不为零时，使用正常的repository_compare
        """
        print("\n=== 测试正常commit ID处理 ===")
        
        # Mock repository_compare的返回值
        mock_comparison = {
            'diffs': [
                {
                    'new_file': True,
                    'new_path': 'new_file.py',
                    'diff': 'new file diff'
                },
                {
                    'new_file': False,
                    'renamed_file': False,
                    'deleted_file': False,
                    'new_path': 'modified_file.py',
                    'diff': 'modified file diff'
                }
            ]
        }
        
        self.mock_project.repository_compare.return_value = mock_comparison
        
        # 调用get_diff_files，使用正常commit ID
        result = gitlab_code.get_diff_files(self.mock_project, "commit1", "commit2")
        
        # 验证repository_compare被调用
        self.mock_project.repository_compare.assert_called_once_with("commit1", "commit2")
        
        # 验证返回结果
        expected_result = {
            'new_file.py': 'new file diff',
            'modified_file.py': 'modified file diff'
        }
        self.assertEqual(result, expected_result)
        print(f"✅ 正常commit ID处理正确，返回{len(result)}个文件")
    
    def test_get_commit_files(self):
        """
        测试get_commit_files函数
        验证能正确获取指定提交的所有文件
        """
        print("\n=== 测试get_commit_files函数 ===")
        
        # Mock commit对象和diff数据
        mock_commit = Mock()
        mock_diffs = [
            {
                'new_path': 'src/main.py',
                'diff': '+print("Hello World")\n'
            },
            {
                'new_path': 'README.md', 
                'diff': '+# Project Title\n'
            }
        ]
        
        mock_commit.diff.return_value = mock_diffs
        self.mock_project.commits.get.return_value = mock_commit
        
        # 调用get_commit_files
        result = gitlab_code.get_commit_files(self.mock_project, self.normal_commit)
        
        # 验证commits.get被调用
        self.mock_project.commits.get.assert_called_once_with(self.normal_commit)
        
        # 验证commit.diff被调用
        mock_commit.diff.assert_called_once()
        
        # 验证返回结果
        expected_result = {
            'src/main.py': '+print("Hello World")\n',
            'README.md': '+# Project Title\n'
        }
        self.assertEqual(result, expected_result)
        print(f"✅ get_commit_files函数正确，返回{len(result)}个文件")
    
    def test_get_rules_zero_commit(self):
        """
        测试get_rules函数对零commit ID的处理
        验证当commit_id为零时，使用branch作为ref
        """
        print("\n=== 测试get_rules零commit ID处理 ===")
        
        # Mock repository_tree返回值
        mock_tree_items = [
            {'name': 'rule1.yaml', 'type': 'blob'},
            {'name': 'rule2.yaml', 'type': 'blob'}
        ]
        self.mock_project.repository_tree.return_value = mock_tree_items
        
        # Mock文件内容
        mock_file_content = "name: test_rule\nmode: diff\n"
        
        with patch.object(gitlab_code, 'get_gitlab_file_content', return_value=mock_file_content):
            # 调用get_rules，使用零commit ID
            result = gitlab_code.get_rules(self.mock_project, self.zero_commit, self.branch_name)
            
            # 验证repository_tree使用branch作为ref
            self.mock_project.repository_tree.assert_called_once_with(
                path='.codereview', 
                ref=self.branch_name,  # 应该使用branch而不是零commit ID
                recursive=True
            )
            
            # 验证返回结果
            self.assertEqual(len(result), 2)
            print(f"✅ get_rules零commit ID处理正确，使用branch作为ref，返回{len(result)}个规则")
    
    def test_get_rules_normal_commit(self):
        """
        测试get_rules函数对正常commit ID的处理
        验证当commit_id不为零时，使用commit_id作为ref
        """
        print("\n=== 测试get_rules正常commit ID处理 ===")
        
        # Mock repository_tree返回值
        mock_tree_items = [
            {'name': 'rule1.yaml', 'type': 'blob'}
        ]
        self.mock_project.repository_tree.return_value = mock_tree_items
        
        # Mock文件内容
        mock_file_content = "name: test_rule\nmode: diff\n"
        
        with patch.object(gitlab_code, 'get_gitlab_file_content', return_value=mock_file_content):
            # 调用get_rules，使用正常commit ID
            result = gitlab_code.get_rules(self.mock_project, self.normal_commit, self.branch_name)
            
            # 验证repository_tree使用commit_id作为ref
            self.mock_project.repository_tree.assert_called_once_with(
                path='.codereview',
                ref=self.normal_commit,  # 应该使用commit_id
                recursive=True
            )
            
            # 验证返回结果
            self.assertEqual(len(result), 1)
            print(f"✅ get_rules正常commit ID处理正确，使用commit_id作为ref，返回{len(result)}个规则")
    
    def test_get_commit_files_exception_handling(self):
        """
        测试get_commit_files函数的异常处理
        验证当GitLab API出错时，正确抛出CodelibException
        """
        print("\n=== 测试get_commit_files异常处理 ===")
        
        # Mock commits.get抛出异常
        self.mock_project.commits.get.side_effect = Exception("GitLab API Error")
        
        # 验证抛出CodelibException
        with self.assertRaises(base.CodelibException) as context:
            gitlab_code.get_commit_files(self.mock_project, self.normal_commit)
        
        # 验证异常信息
        self.assertIn("Fail to get commit files", str(context.exception))
        print("✅ get_commit_files异常处理正确")


def run_tests():
    """运行所有测试"""
    print("🚀 开始GitLab代码功能单元测试...")
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGitLabFunctions)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出测试结果摘要
    print(f"\n📊 测试结果摘要:")
    print(f"   总测试数: {result.testsRun}")
    print(f"   成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   失败: {len(result.failures)}")
    print(f"   错误: {len(result.errors)}")
    
    if result.failures:
        print(f"\n❌ 失败的测试:")
        for test, traceback in result.failures:
            print(f"   - {test}: {traceback}")
    
    if result.errors:
        print(f"\n💥 错误的测试:")
        for test, traceback in result.errors:
            print(f"   - {test}: {traceback}")
    
    # 返回测试是否全部通过
    return len(result.failures) == 0 and len(result.errors) == 0


if __name__ == "__main__":
    success = run_tests()
    if success:
        print(f"\n✅ 所有GitLab代码功能测试通过！")
        exit(0)
    else:
        print(f"\n❌ 部分GitLab代码功能测试失败！")
        exit(1)
