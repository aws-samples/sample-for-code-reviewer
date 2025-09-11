"""
pytest配置文件

这个文件会在pytest运行时自动加载，设置测试环境。
"""

import pytest
import sys
import os

# 添加测试目录到路径
sys.path.insert(0, os.path.dirname(__file__))

def pytest_configure(config):
    """
    pytest配置钩子
    
    在测试开始前自动设置测试环境变量
    """
    from test_config import setup_test_environment, print_test_config
    
    print("\n🧪 正在设置测试环境...")
    setup_test_environment()
    print_test_config()

def pytest_unconfigure(config):
    """
    pytest清理钩子
    
    在测试结束后清理测试环境变量
    """
    from test_config import cleanup_test_environment
    
    print("\n🧹 正在清理测试环境...")
    cleanup_test_environment()

@pytest.fixture(scope="session", autouse=True)
def test_environment():
    """
    测试环境fixture
    
    确保每个测试会话都有正确的环境配置
    """
    from test_config import setup_test_environment, cleanup_test_environment
    
    # 设置环境
    setup_test_environment()
    
    yield
    
    # 清理环境
    cleanup_test_environment()