#!/usr/bin/env python3
"""
GitLab Mock测试辅助工具
提供便捷的Mock GitLab Project对象创建和配置功能
"""

from unittest.mock import Mock, patch
from pathlib import Path
import sys

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from mock_repository_manager import get_mock_gitlab_project


class GitLabMockHelper:
    """GitLab Mock测试辅助类"""
    
    def __init__(self, project_id: str = "123"):
        """
        初始化Mock辅助工具
        
        Args:
            project_id: 项目ID，默认为"123"
        """
        self.project_id = project_id
        self.mock_project = None
    
    def get_mock_project(self):
        """获取Mock的GitLab Project对象"""
        if self.mock_project is None:
            self.mock_project = get_mock_gitlab_project(self.project_id)
        return self.mock_project
    
    def patch_gitlab_project(self, target_path: str):
        """
        创建一个patch装饰器，用于替换指定路径的GitLab Project对象
        
        Args:
            target_path: 要patch的目标路径，如 'lambda.gitlab_code.get_gitlab_project'
            
        Returns:
            patch装饰器
        """
        def mock_get_gitlab_project(*args, **kwargs):
            return self.get_mock_project()
        
        return patch(target_path, side_effect=mock_get_gitlab_project)
    
    def create_simple_mock_project(self, files_data: dict = None):
        """
        创建一个简单的Mock Project对象，用于快速测试
        
        Args:
            files_data: 文件数据字典，格式为 {file_path: content}
            
        Returns:
            Mock Project对象
        """
        if files_data is None:
            files_data = {
                "README.md": "# Test Project\n\nThis is a test project.",
                ".codereview.yaml": "branch: main\nmode: diff\ntarget: '**'"
            }
        
        mock_project = Mock()
        
        # Mock files.raw方法
        def mock_files_raw(file_path, ref):
            if file_path in files_data:
                return files_data[file_path].encode('utf-8')
            else:
                from mock_repository_manager import GitlabGetError
                raise GitlabGetError("File not found", response_code=404)
        
        mock_project.files.raw.side_effect = mock_files_raw
        
        # Mock repository_tree方法
        def mock_repository_tree(path="", ref="main", recursive=True):
            return [
                {
                    'name': Path(file_path).name,
                    'path': file_path,
                    'type': 'blob',
                    'id': f"blob_{hash(file_path)}",
                    'mode': '100644'
                }
                for file_path in files_data.keys()
                if not path or file_path.startswith(path)
            ]
        
        mock_project.repository_tree.side_effect = mock_repository_tree
        
        # Mock其他常用方法
        mock_project.branches.get.return_value = {
            'commit': {'id': 'mock_commit_id_123456'}
        }
        
        mock_project.repository_compare.return_value = {'diffs': []}
        
        return mock_project


# 全局辅助实例
gitlab_mock_helper = GitLabMockHelper()


def get_simple_mock_project(files_data: dict = None):
    """
    获取简单Mock Project对象的便捷函数
    
    Args:
        files_data: 文件数据字典
        
    Returns:
        Mock Project对象
    """
    return gitlab_mock_helper.create_simple_mock_project(files_data)


def patch_gitlab_project(target_path: str):
    """
    Patch GitLab Project的便捷装饰器
    
    Args:
        target_path: 要patch的目标路径
        
    Returns:
        patch装饰器
    """
    return gitlab_mock_helper.patch_gitlab_project(target_path)


if __name__ == "__main__":
    # 测试简单Mock功能
    print("=== 测试简单Mock功能 ===")
    
    # 创建简单Mock
    simple_project = get_simple_mock_project({
        "test.py": "print('Hello World')",
        "config.yaml": "debug: true"
    })
    
    # 测试文件获取
    content = simple_project.files.raw(file_path="test.py", ref="main")
    print(f"✓ 获取文件内容: {content.decode('utf-8')}")
    
    # 测试文件树
    tree = simple_project.repository_tree()
    print(f"✓ 文件树包含 {len(tree)} 个文件")
    for item in tree:
        print(f"  - {item['path']}")
    
    print("=== 简单Mock测试完成 ===")