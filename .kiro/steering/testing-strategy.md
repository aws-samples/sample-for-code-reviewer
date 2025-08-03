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

### GitLab API Mock策略

使用unittest.mock.patch直接Mock gitlab_code.py中的函数，基于函数参数返回预设的仿真数据。不需要启动HTTP服务器，只需要在测试时替换函数实现。

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

**单元测试**：GitLab API使用Mock，AWS服务使用真实资源（测试环境AKSK），Bedrock使用真实服务。

**集成测试**：GitLab API继续使用Mock（避免依赖真实仓库），AWS服务和Bedrock都使用真实资源进行端到端验证。

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

## 测试工具和依赖

### 核心依赖
- pytest：测试框架
- pytest-cov：覆盖率报告
- pytest-mock：Mock支持
- pytest-xdist：并行测试
- boto3：AWS SDK
- responses：HTTP Mock（如需要）
- factory-boy：测试数据工厂
- faker：假数据生成

### Diff生成
使用Python内置difflib库，无需额外依赖。

## 测试最佳实践

### 命名约定
测试文件使用`test_<module_name>.py`格式，测试类使用`Test<ClassName>`，测试方法使用`test_<specific_behavior>()`。

### 组织原则
每个Lambda函数对应一个测试文件，按功能分组测试方法，使用setup/teardown管理测试状态。

### Mock策略
优先Mock外部依赖，保持Mock数据的真实性，确保Mock和真实实现的一致性。

### 断言策略
使用具体的断言而非通用断言，测试正常路径和异常路径，验证副作用（如数据库写入、API调用）。