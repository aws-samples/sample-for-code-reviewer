# 测试策略与设计

## 测试架构概览

采用测试金字塔结构：单元测试70%，集成测试20%，端到端测试10%。重点关注Lambda函数逻辑测试、AWS服务集成和完整业务流程验证。

## 单元测试策略

### 核心Lambda函数测试覆盖

**request_handler.py** - 测试webhook接收和请求创建，包括GitLab push/merge事件处理、手动评审请求、错误处理（无效JSON、缺失字段）、边界条件（大payload、特殊字符）。

**task_dispatcher.py** - 测试请求分解为任务并发送到SQS，包括不同模式的任务创建（diff/single/all）、多规则处理、分支和文件模式匹配、SQS消息发送和失败处理。

**task_executor.py** - 测试Bedrock任务执行和结果处理，包括成功调用、响应解析、不同Claude模型、错误处理（API错误、超时、无效响应）、重试机制、结果存储。

**result_checker.py** - 测试进度跟踪和完成检查，包括进度计算、完成检测、部分完成处理、报告触发、超时处理、状态查询。

**report.py** - 测试HTML报告生成和S3上传，包括模板字段替换、多任务聚合、空结果处理、S3上传、URL生成、代码diff格式化。

**rule_loader.py** - 测试评审规则加载和解析，包括.codereview目录扫描、YAML解析、规则验证、分支模式匹配、错误处理（无效YAML、缺失字段）。

**gitlab_code.py** - 测试GitLab API集成，包括项目信息获取、文件内容获取、仓库树获取、提交差异获取、错误处理（网络超时、凭证无效、项目不存在）。

**base.py** - 测试通用工具函数，包括JSON处理、结构化日志、文件模式匹配、字符串处理。

## Mock系统设计

### Mock策略总则

**黄金法则**：只Mock真正不可控的外部依赖，让业务逻辑真实执行。

**允许Mock的对象**：
- **GitLab Project对象**：通过python-gitlab库访问的GitLab API调用
- **未来扩展**：GitHub、CodeCommit等其他代码仓库的API对象

**禁止Mock的对象**：
- **AWS服务**：DynamoDB、SQS、SNS、Lambda、S3等必须使用真实的测试环境资源
- **业务逻辑模块**：codelib.py、base.py等自定义模块的函数
- **数据处理逻辑**：JSON解析、字符串处理、文件过滤等核心逻辑

### GitLab Project对象Mock策略

基于对`gitlab_code.py`的分析，需要Mock的GitLab Project对象及其方法：

#### 1. repository_compare() - 获取提交差异
**调用位置**：`get_diff_files()`
**Mock对象**：`project.repository_compare(from_commit_id, to_commit_id)`
**返回结构**：
```python
{
    'diffs': [
        {
            'new_file': bool,
            'renamed_file': bool, 
            'deleted_file': bool,
            'old_path': str,
            'new_path': str,
            'diff': str  # 实际的diff内容
        }
    ]
}
```

#### 2. files.raw() - 获取文件原始内容
**调用位置**：`get_gitlab_file()`, `get_gitlab_file_content()`
**Mock对象**：`project.files.raw(file_path=path, ref=ref)`
**返回结构**：`bytes` (需要.decode()转换为字符串)
**Mock策略**：根据file_path和ref返回对应的文件内容

#### 3. repository_tree() - 获取仓库文件树
**调用位置**：`get_rules()`, `get_project_code_text()`
**Mock对象**：`project.repository_tree(path=folder, ref=ref, recursive=True)`
**返回结构**：
```python
[
    {
        'name': str,      # 文件名
        'path': str,      # 完整路径
        'type': str,      # 'blob' 或 'tree'
        'id': str,        # Git对象ID
        'mode': str       # 文件权限
    }
]
```

#### 4. files.get() - 获取文件对象
**调用位置**：`put_rule()`
**Mock对象**：`project.files.get(file_path=filepath, ref=branch)`
**返回结构**：文件对象，包含content属性和save()方法
**异常处理**：404错误表示文件不存在

#### 5. files.create() - 创建新文件
**调用位置**：`put_rule()`
**Mock对象**：`project.files.create({...})`
**参数结构**：
```python
{
    'file_path': str,
    'branch': str,
    'content': str,
    'commit_message': str
}
```

#### 6. branches.get() - 获取分支信息
**调用位置**：`get_last_commit_id()`
**Mock对象**：`project.branches.get(branch)`
**返回结构**：
```python
{
    'commit': {
        'id': str  # 最新提交ID
    }
}
```

#### 7. commits.list() - 获取提交列表
**调用位置**：`get_first_commit_id()`
**Mock对象**：`project.commits.list(ref_name=branch, all=True, order_by='created_date', sort='desc')`
**返回结构**：
```python
[
    {
        'id': str,
        'parent_ids': list  # 父提交ID列表，空列表表示首次提交
    }
]
```

### Mock实现策略

#### 1. 使用unittest.mock.Mock创建Project对象
```python
from unittest.mock import Mock, MagicMock

# 创建mock project对象
mock_project = Mock()

# 配置各个方法的返回值
mock_project.repository_compare.return_value = {...}
mock_project.files.raw.return_value = b"file content"
mock_project.repository_tree.return_value = [...]
```

#### 2. 基于参数的动态返回值
```python
def mock_files_raw(file_path, ref):
    # 根据文件路径和ref返回对应内容
    if file_path == 'src/app.py' and ref == 'commit_123':
        return b"python code content"
    elif file_path == '.codereview/rules.yaml':
        return b"yaml content"
    else:
        raise GitlabGetError("File not found", response_code=404)

mock_project.files.raw.side_effect = mock_files_raw
```

#### 3. 异常情况Mock
```python
from gitlab.exceptions import GitlabGetError, GitlabAuthenticationError

# Mock 404错误
def mock_get_nonexistent_file(file_path, ref):
    raise GitlabGetError("Not found", response_code=404)

# Mock 认证错误  
def mock_auth_error():
    raise GitlabAuthenticationError("Invalid token")
```

#### 4. 仿真数据管理
使用`test/mock_data/repositories/`目录存储仿真仓库数据：
- 每个仓库一个子目录
- 按commit_id组织文件版本
- 支持动态生成diff内容
- 维护分支和提交的关系

### Mock验证原则

#### 1. 参数验证
验证Mock方法被调用时的参数是否正确：
```python
mock_project.files.raw.assert_called_with(
    file_path='src/app.py', 
    ref='commit_123'
)
```

#### 2. 调用次数验证
验证API调用的频率是否符合预期：
```python
assert mock_project.repository_tree.call_count == 1
```

#### 3. 调用顺序验证
对于有依赖关系的API调用，验证调用顺序：
```python
expected_calls = [
    call.repository_tree(ref='main', all=True, recursive=True),
    call.files.raw(file_path='src/app.py', ref='main')
]
mock_project.assert_has_calls(expected_calls)
```

### Mock数据一致性

#### 1. 版本一致性
确保同一commit_id下的所有文件内容保持一致

#### 2. 分支一致性  
确保分支的最新提交与文件内容匹配

#### 3. 差异一致性
确保repository_compare返回的diff与实际文件内容变化一致

#### 4. 异常一致性
确保异常情况的Mock与真实GitLab API行为一致

### 动态Diff生成的仿真仓库

核心思路是维护一个版本化的数据结构，但文件内容存储在文件系统中而不是内存中。

**数据结构设计**：`{ branch: [ { commit_id, message, files: [ file_path_list ] } ] }`

**文件系统组织**：
```
test/mock_data/
├── repositories/
│   └── repo_123/
│       └── main/
│           ├── commit_001/
│           │   ├── src/
│           │   │   └── app.py
│           │   ├── .codereview/
│           │   │   └── python-quality.yaml
│           │   └── README.md
│           ├── commit_002/
│           │   ├── src/
│           │   │   └── app.py
│           │   ├── .codereview/
│           │   │   ├── python-quality.yaml
│           │   │   └── security-check.yaml
│           │   └── README.md
│           └── commit_003/
│               └── ...
```

**工作机制**：
- 元数据（commit信息、文件列表）存储在内存中的数据结构
- 实际文件内容存储在`test/mock_data/repositories/{project_id}/{branch}/{commit_id}/`目录下
- 获取文件内容时从对应目录读取文件
- 生成diff时读取两个commit目录下的对应文件进行比较

**优势**：
- 避免大量文本内容占用内存
- 文件内容可以直接编辑和版本管理
- 支持二进制文件和大文件
- 更真实地模拟文件系统操作

### 测试环境策略

**关键原则**：对于核心业务逻辑验证，使用真实的AWS服务而非Mock

**测试分类原则**：
- **单元测试**：测试单个函数或模块的逻辑正确性
- **集成测试**：测试模块间协作和真实AWS服务集成
- **端到端测试**：测试完整业务流程的正确性

**测试边界原则**：
- 单元测试的边界是当前模块的职责范围
- 不测试外部依赖的具体实现
- 通过真实服务验证集成效果

**单元测试策略**：
- **GitLab Project对象**：Mock project.repository_compare、project.files.raw等API调用，避免依赖外部服务
- **DynamoDB**：使用真实的测试环境DynamoDB表，通过直接读取数据验证写入结果
- **Lambda调用**：使用真实的Lambda异步调用，验证实际的触发和执行效果
- **SQS/SNS**：使用真实服务，验证消息传递的完整性
- **Bedrock**：使用真实服务进行AI模型调用测试

**集成测试策略**：
- **GitLab Project对象**：继续Mock project相关API调用（避免依赖真实仓库）
- **AWS服务**：全部使用真实资源进行端到端验证
- **数据验证**：通过直接查询数据库、队列状态等方式验证业务逻辑

**测试验证原则**：
1. **数据库操作验证**：不Mock DynamoDB，直接读取表数据验证写入结果
2. **Lambda触发验证**：不Mock Lambda客户端，让Lambda真实执行并验证其副作用
3. **消息队列验证**：不Mock SQS/SNS，验证消息的实际发送和处理
4. **状态变更验证**：通过查询实际的系统状态来验证业务逻辑正确性

## 核心测试原则

### Mock使用原则

**黄金法则**：在做任何Mock之前，先回答"这个步骤不Mock不行吗？"

**Mock层级策略**：
- **只Mock最底层的不可控外部依赖**：如GitLab Project对象的API调用（`project.repository_compare()`、`project.files.raw()`等）
- **让业务逻辑层真实执行**：如参数解析、数据处理、状态管理
- **使用真实的AWS服务**：DynamoDB、Lambda、SQS、SNS等用于验证实际效果

**错误的Mock方式**：
- ❌ Mock整个业务逻辑模块（如`codelib.parse_webtool_parameters()`）
- ❌ Mock AWS服务来"提高通过率"
- ❌ 过度简化输入数据

**正确的Mock方式**：
- ✅ 只Mock GitLab Project对象的API方法（`project.repository_compare()`、`project.files.raw()`等）
- ✅ 构造丰富的真实输入数据
- ✅ 让业务逻辑真实执行，发现真实问题

### 推荐的Mock实现方式

**最佳实践：直接使用Mock Data系统，避免patch装饰器**

```python
def test_function(self):
    """推荐的Mock方式：直接使用Mock Data系统"""
    from mock_repository_manager import get_mock_gitlab_project
    
    # 直接创建Mock GitLab Project对象
    mock_project = get_mock_gitlab_project("123")
    
    # 直接构造repo_context，跳过init_repo_context调用
    repo_context = {'source': 'gitlab', 'project': mock_project}
    
    # 让所有业务逻辑真实执行
    result = module_under_test.function(repo_context, other_params)
    
    # 验证结果
    assert result is not None
```

**避免的Mock方式：使用patch装饰器容易造成逻辑矛盾**

```python
# ❌ 错误方式：容易造成重复Mock和逻辑矛盾
@patch('module.init_gitlab_context')
def test_function(self, mock_init_gitlab_context):
    mock_project = get_mock_gitlab_project("123")  # 创建Mock对象
    mock_init_gitlab_context.return_value = mock_project  # 又设置patch返回值
    # 这种方式存在逻辑矛盾：既patch了函数，又手动创建Mock对象
```

**推荐方式的优势**：
- ✅ **逻辑清晰**：没有patch和手动Mock的矛盾
- ✅ **代码简洁**：不需要管理patch装饰器的参数和路径
- ✅ **符合规范**：只Mock GitLab Project对象，让业务逻辑真实执行
- ✅ **维护简单**：直接使用现有的Mock Data系统
- ✅ **测试覆盖完整**：所有codelib和gitlab_code业务逻辑都真实执行

### 测试目的原则

**测试是为了发现问题，不是为了通过**：
- 测试应该能发现真实环境中的问题
- 过度Mock会隐藏真实问题
- 真实的测试失败比虚假的测试通过更有价值

**验证策略**：
- 通过直接读取数据库验证数据写入
- 通过检查系统状态变化验证业务逻辑
- 通过等待异步处理验证完整流程

### 测试失败处理原则

**失败分析策略**：
- 真实的测试失败比虚假的测试通过更有价值
- 测试失败时，首先分析是代码问题还是环境问题
- 区分业务逻辑错误和基础设施配置错误

**问题定位方法**：
- 检查环境变量配置是否正确
- 验证AWS资源是否存在和可访问
- 分析日志输出确定失败原因
- 使用环境检查工具验证配置

**修复优先级**：
1. 环境配置问题（资源不存在、权限不足）
2. 业务逻辑问题（代码错误、逻辑缺陷）
3. 测试设计问题（Mock不当、验证不充分）

## 集成测试设计

### 真实AWS环境测试

使用测试环境的AKSK，确保DynamoDB表、SQS队列、S3存储桶等资源存在。测试前设置测试数据，测试后清理数据但保留基础设施。

### 端到端流程测试

**完整webhook流程**：发送webhook事件 → 验证请求创建 → 验证任务分发 → 模拟任务执行 → 验证进度跟踪 → 验证报告生成 → 验证通知发送。

**手动评审流程**：通过API手动触发评审，验证整个处理链路。

**多规则并行处理**：测试同一个代码变更匹配多个评审规则的场景。

**超时处理流程**：模拟长时间运行的任务，验证15分钟超时机制。

### 性能和负载测试

测试并发webhook处理能力、大型仓库处理性能、内存使用情况、处理时间等关键指标。

## 测试数据管理

### 测试数据工厂

提供创建各种测试场景数据的工厂方法：webhook事件数据、仓库数据、不同编程语言和复杂度的代码文件。

### 测试环境隔离

每个测试使用独立的数据环境，测试前创建隔离环境，测试后自动清理资源，避免测试间相互影响。

## 测试执行策略

### 本地开发测试
- 快速单元测试：`pytest test/unit/ -v --tb=short`
- 带覆盖率测试：`pytest test/unit/ -v --cov=lambda --cov-report=html`
- 特定模块测试：`pytest test/unit/test_task_dispatcher.py -v`

### CI/CD集成测试
- 完整测试套件：`pytest test/ -v --junitxml=test-results.xml`
- 并行测试执行：`pytest test/ -n auto`
- 集成测试（需要AWS凭证）：`pytest test/integration/ -v --aws-profile=test`

### 测试分类标记
使用pytest标记系统区分不同类型的测试：@pytest.mark.unit、@pytest.mark.integration、@pytest.mark.slow、@pytest.mark.aws_required等。

## 环境配置管理

### 测试环境变量策略

**必须配置的环境变量**：
- **数据库表名**：REQUEST_TABLE, TASK_TABLE, RULE_TABLE, REPOSITORY_TABLE
- **AWS服务资源**：BUCKET_NAME, TASK_SQS_URL, SNS_TOPIC_ARN, TASK_DISPATCHER_FUN_NAME
- **邮件配置**：SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD
- **报告配置**：REPORT_SENDER, REPORT_RECEIVER, REPORT_TIMEOUT_SECONDS

**不需要配置的环境变量**：
- Bedrock相关配置（通过其他方式处理）
- 带默认值的系统参数（SQS_MAX_DELAY等）
- AWS自动设置的环境变量

**配置管理原则**：
- 使用独立的测试环境资源（demo环境）
- 通过`test_config.py`集中管理配置
- 支持用户自定义配置覆盖
- 自动设置和清理环境变量

### 测试环境隔离

**资源命名策略**：
- 所有测试资源使用统一前缀（如`code-reviewer-demo-`）
- 避免与生产环境资源冲突
- 使用独立的AWS账户或区域

**环境生命周期管理**：
- 测试前自动设置环境变量
- 测试后自动清理环境变量
- 提供环境检查和验证工具

## 测试工具和依赖

### 核心依赖
- pytest：测试框架
- pytest-cov：覆盖率报告
- pytest-mock：Mock支持
- pytest-xdist：并行测试
- boto3：AWS SDK（用于真实服务调用）
- responses：HTTP Mock（仅用于外部API）

### 测试配置工具
- test_config.py：环境变量配置管理
- conftest.py：pytest自动配置
- check_test_env.py：环境验证脚本

### Diff生成
使用Python内置difflib库，无需额外依赖。

## 测试最佳实践

### 命名约定
- **测试文件**：使用`test_<module_name>.py`格式
- **测试设计文档**：使用`test_<module_name>.md`格式，与对应的测试文件同名
- **测试类**：使用`Test<ClassName>`格式
- **测试方法**：使用`test_<specific_behavior>()`格式

### 组织原则
每个Lambda函数对应一个测试文件，按功能分组测试方法，使用setup/teardown管理测试状态。

### 测试文档规范

**测试设计文档要求**：
- 每个测试用例Python文件（如`test_module.py`）必须配套一个测试设计文档（如`test_module.md`）
- 测试设计文档用于详细阐述测试思路、策略和设计考虑
- 测试Python文件中只保留简洁的测试目标说明，详细设计思路写在对应的md文档中

**测试设计文档结构**：
```markdown
# test_module.py 测试用例设计文档

## 模块概述
- 被测试模块的作用和业务重要性

## 业务流程分析
- 主要业务步骤和关键逻辑分析

## 测试用例设计
### 1. 测试用例名称 (test_function_name)
#### 测试目标
#### 测试场景
#### 测试流程
#### 关键验证点
#### 期望结果

## 测试策略
- Mock策略
- 验证方法
- 测试数据管理

## 业务价值
- 测试的重要性和价值说明
```

**文档管理原则**：
- 测试设计文档与测试代码同步维护
- 设计文档作为测试实现的指导和评审依据
- 通过设计文档确保测试覆盖的完整性和合理性

### 测试注释规范

**测试用例注释结构**：
```python
def test_function_name(self):
    """
    测试目的：明确说明要验证什么功能
    
    测试场景：描述具体的业务情况
    业务重要性：解释为什么这个测试很重要
    
    测试流程：
    1. 准备测试数据：具体的准备步骤
    2. 执行核心功能：调用被测试函数
    3. 验证结果：检查预期结果
    4. 清理数据：清理测试环境
    
    关键验证点：
    - 列出主要的验证点
    - 说明业务意义
    
    期望结果：
    - 明确的成功标准
    """
```

**注释原则**：
- 用"测试流程"而非"测试策略"
- 让读者不看代码就能理解测试过程
- 包含业务意义和重要性说明
- 提供故障排除信息

### Mock策略
- **最小化原则**：只Mock真正不可控的外部依赖
- **真实性原则**：让业务逻辑真实执行
- **层级原则**：Mock最底层的API调用，不Mock业务逻辑层

### 断言策略
- 使用具体的断言而非通用断言
- 测试正常路径和异常路径
- 验证副作用（如数据库写入、状态变更）
- 通过真实系统状态验证结果

### 数据管理策略
- 构造丰富的真实测试数据
- 每个测试后清理数据避免污染
- 使用独立的测试环境资源
- 验证数据的完整性和正确性

## Mock最佳实践示例

### 推荐的实现方式

基于我们在`test_get_code_contents`中的实践，以下是推荐的Mock实现方式：

```python
def test_get_code_contents(self):
    """
    最佳实践示例：直接使用Mock Data系统
    
    优势：
    - 逻辑清晰，无patch装饰器复杂性
    - 让所有业务逻辑真实执行
    - 只Mock最底层的GitLab Project对象
    - 符合测试策略规范
    """
    from mock_repository_manager import get_mock_gitlab_project
    
    # 直接创建Mock GitLab Project对象（这是允许Mock的外部依赖）
    mock_project = get_mock_gitlab_project("123")
    
    # 直接构造repo_context，跳过init_repo_context的调用
    # 这样我们只Mock了GitLab Project对象，让codelib和gitlab_code的业务逻辑真实执行
    repo_context = {'source': 'gitlab', 'project': mock_project}
    
    # 使用真实的commit ID和规则
    commit_id = 'b2c3d4e5f6789012345678901234567890abcdef'
    rule = {'name': '测试规则', 'mode': 'all', 'target': 'src/**/*.java'}
    
    # 调用被测试函数（让所有业务逻辑真实执行）
    contents = task_dispatcher.get_code_contents_for_all(repo_context, commit_id, rule)
    
    # 验证结果
    assert len(contents) == 1
    assert contents[0]['mode'] == 'all'
    assert contents[0]['content'] is not None
```

### 避免的错误方式

```python
# ❌ 错误方式1：Mock业务逻辑模块
@patch('task_dispatcher.codelib.get_project_code_text')
def test_get_code_contents(self, mock_get_project_code_text):
    # 这种方式Mock了业务逻辑，违反了测试策略
    pass

# ❌ 错误方式2：重复Mock造成逻辑矛盾
@patch('gitlab_code.init_gitlab_context')
def test_get_code_contents(self, mock_init_gitlab_context):
    mock_project = get_mock_gitlab_project("123")  # 创建Mock对象
    mock_init_gitlab_context.return_value = mock_project  # 又设置patch返回值
    # 这种方式存在逻辑矛盾：既patch了函数，又手动创建Mock对象
```

### 关键原则总结

1. **直接使用Mock Data系统**：避免patch装饰器的复杂性
2. **只Mock外部依赖**：GitLab Project对象是唯一允许Mock的对象
3. **让业务逻辑真实执行**：所有codelib和gitlab_code函数都应该真实运行
4. **逻辑清晰**：避免重复Mock和逻辑矛盾
5. **测试覆盖完整**：能够发现真实的业务逻辑问题

这种方式完美体现了测试策略的**黄金法则**：
> **只Mock真正不可控的外部依赖，让业务逻辑真实执行**