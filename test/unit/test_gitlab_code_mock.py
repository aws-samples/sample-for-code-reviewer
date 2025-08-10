#!/usr/bin/env python3
"""
测试gitlab_code.py模块的Mock版本
使用Mock仓库管理器模拟GitLab API调用
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, Mock

# 添加lambda目录到Python路径
lambda_dir = Path(__file__).parent.parent.parent / "lambda"
sys.path.insert(0, str(lambda_dir))

# 添加mock数据目录到Python路径
mock_dir = Path(__file__).parent.parent / "mock_data" / "repositories"
sys.path.insert(0, str(mock_dir))

from mock_repository_manager import get_mock_gitlab_project


class TestGitLabCodeMock:
    """测试GitLab代码集成的Mock版本"""
    
    def test_get_gitlab_file_content_with_mock(self):
        """
        测试目的：验证使用Mock的GitLab文件内容获取功能
        
        测试场景：模拟从GitLab仓库获取指定文件的内容
        业务重要性：这是代码评审系统的核心功能，必须确保能正确获取文件内容
        
        测试流程：
        1. 创建Mock GitLab Project对象
        2. 获取最新commit的文件内容
        3. 验证返回的内容是否正确
        
        关键验证点：
        - 能够成功获取文件内容
        - 返回的文件内容符合预期
        - 文件内容包含正确的Java代码结构
        
        期望结果：
        - 成功获取文件内容
        - 内容包含预期的Java类定义
        """
        # 使用真实的mock仓库数据
        mock_project = get_mock_gitlab_project("123")
        
        # 使用包含App.java的commit
        app_java_commit = "b2c3d4e5f6789012345678901234567890abcdef"
        
        # 测试文件内容获取
        content = mock_project.files.raw(
            file_path="src/main/java/demo/great/App.java", 
            ref=app_java_commit
        )
        
        # 验证结果
        assert content is not None
        decoded_content = content.decode('utf-8')
        assert "public class App" in decoded_content
        assert "package demo.great" in decoded_content
    
    def test_get_repository_tree_with_mock(self):
        """
        测试目的：验证使用Mock的仓库文件树获取功能
        
        测试场景：模拟获取GitLab仓库的文件树结构
        业务重要性：用于扫描仓库中的所有文件，是批量处理的基础
        
        测试流程：
        1. 创建包含多个文件的Mock Project
        2. 调用repository_tree方法
        3. 验证返回的文件树结构
        4. 检查文件路径和类型信息
        
        关键验证点：
        - 返回的文件列表完整
        - 文件路径信息正确
        - 文件类型标记正确
        
        期望结果：
        - 获取完整的文件树
        - 每个文件的元数据正确
        """
        # 使用真实的mock仓库数据
        mock_project = get_mock_gitlab_project("123")
        
        # 获取文件树 - 使用最新commit查看完整项目结构
        latest_commit = "l23456789012345678901234567890123456789"
        tree = mock_project.repository_tree(ref=latest_commit, recursive=True)
        
        # 验证结果 - 真实mock数据包含更多文件
        assert len(tree) > 5, "真实mock数据应该包含多个文件"
        
        # 检查关键文件是否存在
        file_paths = [item['path'] for item in tree]
        assert any("App.java" in path for path in file_paths), "应该包含App.java文件"
        assert any("pom.xml" in path for path in file_paths), "应该包含pom.xml文件"
        assert any(".codereview" in path for path in file_paths), "应该包含代码评审配置文件"
        
        # 检查文件类型
        for item in tree:
            assert item['type'] == 'blob', "所有项目都应该是文件类型"
            assert 'name' in item, "应该包含文件名"
            assert 'id' in item, "应该包含文件ID"
            assert 'mode' in item, "应该包含文件模式"
    
    def test_file_not_found_error_with_mock(self):
        """
        测试目的：验证Mock系统的错误处理机制
        
        测试场景：尝试获取不存在的文件，验证异常处理
        业务重要性：确保系统能正确处理文件不存在的情况
        
        测试流程：
        1. 创建Mock Project
        2. 尝试获取不存在的文件
        3. 验证抛出正确的异常
        4. 检查异常信息
        
        关键验证点：
        - 抛出GitlabGetError异常
        - 异常响应码为404
        - 异常消息合理
        
        期望结果：
        - 正确抛出异常
        - 异常类型和信息符合预期
        """
        # 使用真实的mock仓库数据
        mock_project = get_mock_gitlab_project("123")
        
        # 尝试获取不存在的文件
        latest_commit = "l23456789012345678901234567890123456789"
        with pytest.raises(Exception) as exc_info:
            mock_project.files.raw(
                file_path="nonexistent_file.txt",
                ref=latest_commit
            )
        
        # 验证异常类型和信息
        exception = exc_info.value
        assert "File not found" in str(exception)
        
        # 如果是GitlabGetError，检查响应码
        if hasattr(exception, 'response_code'):
            assert exception.response_code == 404
    
    def test_mock_project_integration(self):
        """
        测试目的：验证Mock Project的完整集成功能
        
        测试场景：模拟完整的GitLab API调用流程
        业务重要性：确保Mock系统能够支持完整的业务流程测试
        
        测试流程：
        1. 创建包含代码评审配置的Mock Project
        2. 测试获取评审规则文件
        3. 测试获取源代码文件
        4. 测试获取分支信息
        5. 验证所有操作的一致性
        
        关键验证点：
        - 所有API调用都能正常工作
        - 返回的数据格式正确
        - Mock行为一致性
        
        期望结果：
        - 完整的API调用流程正常
        - 数据格式符合GitLab API规范
        """
        # 使用真实的mock仓库数据
        mock_project = get_mock_gitlab_project("123")
        
        # 使用包含评审规则的commit
        rules_commit = "d4e5f6789012345678901234567890abcdef1234"
        # 使用包含App.java的commit  
        app_commit = "b2c3d4e5f6789012345678901234567890abcdef"
        # 使用最新commit查看完整结构
        latest_commit = "l23456789012345678901234567890123456789"
        
        # 1. 测试获取评审规则 - 使用真实mock数据中的文件
        codereview_content = mock_project.files.raw(
            file_path=".codereview/code-simplification.yaml",
            ref=rules_commit
        )
        content_text = codereview_content.decode('utf-8')
        assert 'branch: "main"' in content_text or 'branch: main' in content_text
        assert 'mode: "diff"' in content_text or 'mode: diff' in content_text
        
        # 2. 测试获取源代码 - 使用真实mock数据中的文件
        java_content = mock_project.files.raw(
            file_path="src/main/java/demo/great/App.java",
            ref=app_commit
        )
        java_text = java_content.decode('utf-8')
        assert "public class App" in java_text
        
        # 3. 测试获取文件树
        tree = mock_project.repository_tree(ref=latest_commit)
        assert len(tree) > 3, "真实mock数据应该包含多个文件"
        
        # 4. 测试获取分支信息
        branch_info = mock_project.branches.get("main")
        assert 'commit' in branch_info
        assert 'id' in branch_info['commit']
        
        # 5. 验证这是真实的mock项目，不是简单mock
        file_paths = [item['path'] for item in tree]
        assert any("great" in path for path in file_paths), "应该包含great包结构"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])