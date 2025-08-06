# Mock Data 系统

## 概述

Mock Data系统用于在测试中模拟GitLab API调用，避免对真实GitLab服务的依赖。系统提供与python-gitlab完全一致的API接口，使用文件系统中的仿真仓库数据。

## 核心组件

### MockRepositoryManager
- **位置**: `test/mock_data/repositories/mock_repository_manager.py`
- **功能**: 核心Mock仓库管理器，提供完整的GitLab API模拟
- **支持的API**:
  - `repository_compare()` - 提交差异比较
  - `files.raw()` - 获取文件原始内容
  - `repository_tree()` - 获取仓库文件树
  - `files.get()` - 获取文件对象
  - `files.create()` - 创建新文件
  - `branches.get()` - 获取分支信息
  - `commits.list()` - 获取提交列表

### GitLabMockHelper
- **位置**: `test/mock_data/repositories/mock_gitlab_helper.py`
- **功能**: 测试辅助工具，提供便捷的Mock对象创建和配置
- **主要方法**:
  - `get_mock_project()` - 获取完整的Mock Project对象
  - `create_simple_mock_project()` - 创建简化的Mock对象
  - `patch_gitlab_project()` - 创建patch装饰器

## 数据结构

### 仓库元数据
- **文件**: `test/mock_data/repositories/mock_java_project/repository_metadata.json`
- **结构**:
```json
{
  "project_id": "123",
  "project_name": "demo-java-project",
  "branches": {
    "main": {
      "commits": [
        {
          "commit_id": "commit_hash",
          "message": "commit message",
          "parent_ids": ["parent_commit_hash"],
          "files": ["file1.java"],
          "deleted_files": []
        }
      ]
    }
  }
}
```

### 文件系统组织
```
test/mock_data/repositories/mock_java_project/main/
├── commit_id_1/                # 第一个提交的文件状态
│   └── README.md
├── commit_id_2/                # 第二个提交的文件状态
│   ├── README.md
│   └── .gitignore
└── commit_id_3/                # 第三个提交的文件状态
    ├── README.md
    ├── .gitignore
    ├── pom.xml
    └── src/main/java/demo/great/App.java
```

## 使用方法

### 基本用法
```python
from test.mock_data.repositories.mock_gitlab_helper import get_simple_mock_project

# 创建简单的Mock Project
test_files = {
    "README.md": "# Test Project",
    ".codereview.yaml": "branch: main\nmode: diff"
}
mock_project = get_simple_mock_project(test_files)

# 使用Mock Project
content = mock_project.files.raw(file_path="README.md", ref="main")
```

### 完整仓库Mock
```python
from test.mock_data.repositories.mock_repository_manager import get_mock_gitlab_project

# 获取完整的Mock Project（基于mock_java_project数据）
project = get_mock_gitlab_project("123")

# 比较两个提交的差异
diff = project.repository_compare(commit1, commit2)
```

### 在测试中使用Patch
```python
from unittest.mock import patch
from test.mock_data.repositories.mock_gitlab_helper import get_simple_mock_project

class TestMyModule:
    @patch('lambda.gitlab_code.get_gitlab_project')
    def test_my_function(self, mock_get_project):
        # 配置Mock
        mock_get_project.return_value = get_simple_mock_project({
            "test.py": "print('hello')"
        })
        
        # 执行测试
        # ... 你的测试代码
```

## API一致性

Mock Project API与python-gitlab API完全一致：

| 真实API | Mock API | 返回类型 |
|---------|----------|----------|
| `project.files.raw(file_path, ref)` | `mock_project.files.raw(file_path, ref)` | `bytes` |
| `project.repository_tree(ref, recursive)` | `mock_project.repository_tree(ref, recursive)` | `List[Dict]` |
| `project.repository_compare(from, to)` | `mock_project.repository_compare(from, to)` | `Dict` |
| `project.branches.get(branch)` | `mock_project.branches.get(branch)` | `Dict` |
| `project.commits.list(ref_name)` | `mock_project.commits.list(ref_name)` | `List[Dict]` |

## 数据流程

```
测试代码调用 → Mock API → 读取文件系统数据 → 返回真实格式的结果
```

每次API调用时：
- `files.raw()` → 从对应commit目录读取实际文件内容
- `repository_tree()` → 动态计算指定commit的完整文件列表，生成文件树
- `repository_compare()` → 根据`files`和`deleted_files`字段确定变更文件，比较两个commit目录的文件差异生成真实diff
- `branches.get()` → 从metadata.json获取分支最新提交
- `commits.list()` → 从metadata.json获取提交历史

## 数据结构说明

### 动态计算设计
- **files**: 当前commit中新增或修改的文件列表
- **deleted_files**: 当前commit中删除的文件列表
- **完整文件列表**: 从第一个commit开始动态累积计算，确保数据一致性

### 优势
- ✅ **数据源单一**: 避免手动维护all_files导致的不一致
- ✅ **符合Git语义**: 每次commit只记录实际变更
- ✅ **支持文件删除**: 通过deleted_files字段支持删除操作
- ✅ **动态计算**: 任意commit的完整文件列表都是实时计算的
- ✅ **一致性保证**: 不会出现手动编辑导致的数据错误

这种设计确保了：
- `repository_compare()` 只显示实际变更的文件
- `repository_tree()` 显示动态计算的完整仓库文件结构
- 数据一致性得到根本保证

## 异常处理

Mock系统正确模拟GitLab API的异常行为：
- 文件不存在 → `GitlabGetError(404)`
- 提交不存在 → `GitlabGetError(404)`
- 分支不存在 → `GitlabGetError(404)`

## 测试策略集成

Mock Data系统严格遵循测试策略原则：

### 允许Mock的对象
- ✅ **GitLab Project对象**: 通过python-gitlab库访问的GitLab API调用
- ✅ **未来扩展**: GitHub、CodeCommit等其他代码仓库的API对象

### 禁止Mock的对象
- ❌ **AWS服务**: DynamoDB、SQS、SNS、Lambda、S3等必须使用真实的测试环境资源
- ❌ **业务逻辑模块**: codelib.py、base.py等自定义模块的函数
- ❌ **数据处理逻辑**: JSON解析、字符串处理、文件过滤等核心逻辑

### Mock验证原则
- **参数验证**: 验证Mock方法被调用时的参数是否正确
- **调用次数验证**: 验证API调用的频率是否符合预期
- **调用顺序验证**: 对于有依赖关系的API调用，验证调用顺序

## 优势

- ✅ **API接口100%兼容python-gitlab**
- ✅ **返回数据结构完全一致**
- ✅ **支持真实的diff生成**
- ✅ **支持异常情况模拟**
- ✅ **无需网络连接**
- ✅ **测试速度快**
- ✅ **数据可控可重复**
- ✅ **符合测试策略原则**

## 维护指南

### 添加新的仓库数据
1. 在`test/mock_data/repositories/`下创建新的项目目录
2. 创建`repository_metadata.json`文件定义提交历史
3. 按提交ID组织文件结构
4. 更新`MockRepositoryManager`以支持新项目ID

### 添加新的API方法
1. 在`MockRepositoryManager`中添加新的Mock方法
2. 实现相应的业务逻辑
3. 确保返回数据结构与真实API一致
4. 添加异常处理逻辑

### 数据一致性检查
- **版本一致性**: 确保同一commit_id下的所有文件内容保持一致
- **分支一致性**: 确保分支的最新提交与文件内容匹配
- **差异一致性**: 确保repository_compare返回的diff与实际文件内容变化一致
- **异常一致性**: 确保异常情况的Mock与真实GitLab API行为一致