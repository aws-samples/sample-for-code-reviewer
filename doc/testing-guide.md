# 测试指南

本项目提供两种测试方式：本地单元测试和AWS集成测试。

> **相关文档**:
> - [规则格式文档](rule-format.md) - 代码评审规则配置

---

## 📊 测试概述

| 测试类型 | 运行时间 | 需要部署 | 覆盖范围 | 使用场景 |
|---------|---------|---------|---------|---------|
| **本地单元测试** | < 1秒 | ❌ | 核心功能 | 开发阶段快速验证 |
| **集成测试** | 2-5分钟 | ✅ | 完整流程 | 部署前全面验证 |

---

## 🚀 快速开始

### 本地单元测试 (推荐用于日常开发)

```bash
# 安装依赖
pip install pytest boto3

# 运行所有本地测试 (跳过实际 Bedrock API 调用)
python scripts/test_local.py --no-bedrock

# 只测试模型配置 (最快, < 1秒)
python scripts/test_local.py --only model

# 只测试 Bedrock 调用 (跳过实际 API)
python scripts/test_local.py --only bedrock
```

### 集成测试 (用于部署前验证)

```bash
# 配置测试环境 (一次性设置) - 见下方详细说明
# ...

# 测试 Single 模式 (GitHub, Claude 4)
python test/integration/test_rule_single.py github --model claude4

# 测试 All 模式 (GitHub, Claude 4)
python test/integration/test_rule_all.py github --model claude4
```

---

## 📁 测试结构

```
test/
├── unit/                           # 本地单元测试
│   ├── test_model_config.py       # 模型配置测试 ⭐
│   ├── test_bedrock_invoke.py     # Bedrock API 测试 ⭐
│   ├── test_task_dispatcher.py    # 任务分发器测试 (集成)
│   ├── test_request_handler.py    # 请求处理器测试 (集成)
│   └── test_gitlab_code_mock.py   # Mock 数据
│
├── integration/                    # AWS 集成测试
│   ├── test_rule_single.py        # Single 模式测试
│   ├── test_rule_all.py           # All 模式测试
│   └── validation_framework.py    # 验证框架
│
├── mock_data/                      # 测试数据
│   └── repositories/               # Mock仓库数据
│
└── simulation_lib.py              # 测试辅助库

scripts/
└── test_local.py                  # 本地测试运行脚本 ⭐
```

---

## 🔬 本地单元测试详解

### 1. test_model_config.py - 模型配置测试

**测试内容**:
- ✅ 所有 Claude 模型配置 (3/3.5/3.7/4/4.5)
- ✅ model_id 获取和格式化
- ✅ Reasoning 支持检测
- ✅ 版本比较 (>= 3.7)
- ✅ 错误处理

**运行方式**:
```bash
# 方式 1: 使用测试脚本
python scripts/test_local.py --only model

# 方式 2: 直接运行
python test/unit/test_model_config.py

# 方式 3: 使用 pytest
pytest test/unit/test_model_config.py -v
```

**预期输出**:
```
✅ 支持 11 个模型
✅ claude3.7-sonnet: model_id=us.anthropic.claude-3-7-sonnet-20250219-v1:0, reasoning=True
✅ claude4-sonnet: model_id=us.anthropic.claude-sonnet-4-20250514-v1:0, reasoning=False
...
============================== 12 passed in 0.05s ===============================
```

---

### 2. test_bedrock_invoke.py - Bedrock API 调用测试

**测试内容**:
- ✅ Claude 3.5 基本调用
- ✅ Claude 3.7 Extended Thinking 调用
- ✅ Claude 4 Extended Thinking 调用
- ✅ 响应解析 (thinking + text blocks)
- ✅ 错误处理

**如何跳过实际 API 调用**:

pytest 的 `@pytest.mark.skipif` 装饰器会检查环境变量 `SKIP_BEDROCK_TESTS`:

```python
# test_bedrock_invoke.py 中的实现
SKIP_BEDROCK_TESTS = os.environ.get('SKIP_BEDROCK_TESTS', '0') == '1'

@pytest.mark.skipif(SKIP_BEDROCK_TESTS, reason="跳过实际 Bedrock API 调用")
def test_invoke_claude35_basic(self, bedrock_client):
    # 这个测试只在 SKIP_BEDROCK_TESTS != '1' 时运行
    ...
```

**运行方式**:
```bash
# 跳过实际 API 调用 (快速, < 1秒)
SKIP_BEDROCK_TESTS=1 python scripts/test_local.py --only bedrock
# 或
python scripts/test_local.py --no-bedrock

# 实际调用 API (需要 AWS 凭证, 10-30秒)
python scripts/test_local.py --only bedrock

# 直接运行 (跳过 API)
SKIP_BEDROCK_TESTS=1 python test/unit/test_bedrock_invoke.py
```

**预期输出 (跳过 API 调用)**:
```
test_invoke_claude35_basic                      SKIPPED  # API 调用被跳过
test_invoke_claude37_with_extended_thinking     SKIPPED  # API 调用被跳过
test_parse_response_with_thinking               SKIPPED  # API 调用被跳过
test_build_extended_thinking_params             PASSED   # 不需要 API 的测试仍运行
test_model_config_for_all_models                PASSED   # 不需要 API 的测试仍运行
======================== 2 passed, 3 skipped in 0.10s ==========================
```

**预期输出 (实际 API 调用)**:
```
✅ Claude 3.5 响应: Hello

✅ Claude 3.7 Extended Thinking 测试:
   - 包含 thinking: True
   - 包含 text: True
   - Thinking: Let me calculate 15 * 23...
   - Text: 345

✅ Claude 4 Extended Thinking 测试通过
======================== 7 passed in 25.3s ===============================
```

**AWS 凭证要求**:
- 配置 AWS CLI: `aws configure`
- 或设置环境变量:
  ```bash
  export AWS_ACCESS_KEY_ID=xxx
  export AWS_SECRET_ACCESS_KEY=xxx
  export AWS_DEFAULT_REGION=us-east-1
  ```
- 需要 Bedrock 访问权限

---

### 3. scripts/test_local.py - 统一测试入口

**功能**:
- 运行所有或特定的本地单元测试
- 自动设置 `SKIP_BEDROCK_TESTS` 环境变量
- 清晰的输出格式

**命令参数**:
```bash
python scripts/test_local.py [OPTIONS]

OPTIONS:
  --no-bedrock      跳过 Bedrock API 调用测试
  --only {model|bedrock}   只运行指定类型的测试
  -h, --help        显示帮助信息
```

**示例**:
```bash
# 运行所有测试 (跳过 Bedrock API)
python scripts/test_local.py --no-bedrock

# 运行所有测试 (包括 Bedrock API, 需要 AWS 凭证)
python scripts/test_local.py

# 只测试模型配置
python scripts/test_local.py --only model

# 只测试 Bedrock (跳过 API)
python scripts/test_local.py --only bedrock --no-bedrock
```

---

## 🔄 集成测试详解

集成测试验证完整的代码评审流程，包括：
- GitHub/GitLab webhook 触发
- Lambda 函数执行
- DynamoDB 数据存储
- SQS 消息队列
- Bedrock API 调用
- S3 报告生成

> ⚠️ **重要提示**：集成测试需要正确配置 Lambda 环境变量，否则会失败！见下方"常见坑"部分。

---

## ⚙️ 集成测试环境配置

### 步骤 1: 安装测试依赖

```bash
cd /home/ec2-user/working/cr
pip3 install -r test/requirements.txt
pip3 install GitPython python-gitlab PyGithub
```

### 步骤 2: 创建测试仓库

**GitHub** (推荐):
1. 访问 [https://github.com/new](https://github.com/new)
2. 创建测试仓库，建议命名：`code-review-test`
3. 设置为 Public 或 Private (需要相应权限)

**GitLab** (可选):
1. 访问 [https://gitlab.com/projects/new](https://gitlab.com/projects/new)
2. 创建测试仓库：`code-review-test`

### 步骤 3: 生成 Access Token

**GitHub Personal Access Token**:
1. 访问 [https://github.com/settings/tokens](https://github.com/settings/tokens)
2. 点击 "Generate new token (classic)"
3. 设置名称：`code-reviewer-test`
4. **必需权限**：
   - ✅ `repo` - 完整仓库访问权限
5. 生成并**保存** token (只显示一次！)

**GitLab Access Token** (如果使用GitLab):
1. 访问 [https://gitlab.com/-/user_settings/personal_access_tokens](https://gitlab.com/-/user_settings/personal_access_tokens)
2. 创建 Personal Access Token
3. **必需权限**：
   - ✅ `api` - 完整 API 访问
   - ✅ `write_repository` - 写入仓库
5. 生成并保存 token

### 步骤 4: 配置 test_config.json

创建 `test/test_config.json`:

```json
{
  "github": {
    "url": "https://api.github.com",
    "token": "ghp_xxxxxxxxxxxxxxxxxxxx",           // 你的 GitHub token
    "username": "your-github-username",             // 你的 GitHub 用户名
    "test_repo": "code-review-test",                // 测试仓库名
    "project_id": "your-github-username/code-review-test",
    "repo_url": "git@github.com:your-github-username/code-review-test.git",
    "owner": "your-github-username",
    "repo_name": "code-review-test"
  },
  "gitlab": {
    "url": "https://gitlab.com",
    "token": "glpat-xxxxxxxxxxxxxxxxxxxx",          // 你的 GitLab token
    "username": "your-gitlab-username",             // 你的 GitLab 用户名
    "test_repo": "code-review-test",                // 测试仓库名
    "project_id": "your-gitlab-username/code-review-test",
    "repo_url": "git@gitlab.com:your-gitlab-username/code-review-test.git"
  },
  "aws": {
    "endpoint": "https://your-api-gateway-id.execute-api.us-east-1.amazonaws.com/prod",
    "request_table": "your-prefix-request",
    "task_table": "your-prefix-task",
    "sqs_url": "https://sqs.us-east-1.amazonaws.com/account-id/your-prefix-queue",
    "task_dispatcher_function": "your-prefix-task-dispatcher"
  }
}
```

### 步骤 5: 🔴 配置 Lambda 环境变量 (最重要！)

> ⚠️ **这是最常见的测试失败原因！**

**必须配置的 Lambda 函数**:
- `{project_name}-request-handler`
- `{project_name}-task-dispatcher`

**必需的环境变量**:
```bash
ACCESS_TOKEN        # GitHub/GitLab token (不能为空！)
REQUEST_TABLE       # DynamoDB Request 表名
TASK_TABLE          # DynamoDB Task 表名
TASK_SQS_URL        # SQS 队列 URL
SNS_TOPIC_ARN       # SNS Topic ARN
BUCKET_NAME         # S3 bucket 名称
```

**检查环境变量** (推荐第一步！):
```bash
# 检查 request-handler 环境变量
aws lambda get-function-configuration \
  --function-name aws-cr-1p3-request-handler \
  --region us-east-1 \
  --query 'Environment.Variables'

# 检查 task-dispatcher 环境变量
aws lambda get-function-configuration \
  --function-name aws-cr-1p3-task-dispatcher \
  --region us-east-1 \
  --query 'Environment.Variables'
```

**配置环境变量**:
```bash
# 方法 1: 使用 AWS CLI
aws lambda update-function-configuration \
  --function-name aws-cr-1p3-request-handler \
  --environment "Variables={
    ACCESS_TOKEN=ghp_your_token_here,
    REQUEST_TABLE=aws-cr-1p3-request,
    TASK_TABLE=aws-cr-1p3-task,
    TASK_SQS_URL=https://sqs.us-east-1.amazonaws.com/xxx/aws-cr-1p3-queue,
    SNS_TOPIC_ARN=arn:aws:sns:us-east-1:xxx:aws-cr-1p3-topic,
    BUCKET_NAME=aws-cr-1p3-report-bucket
  }" \
  --region us-east-1

# 对 task-dispatcher 重复相同操作
aws lambda update-function-configuration \
  --function-name aws-cr-1p3-task-dispatcher \
  --environment "Variables={...}" \
  --region us-east-1
```

**方法 2: 通过 AWS Console**:
1. 打开 Lambda 控制台
2. 选择函数 → Configuration → Environment variables
3. 添加/编辑上述环境变量

### 步骤 6: 初始化 Webhook

```bash
cd test
python3 init_webhook.py
```

**预期输出**:
```
✅ GitHub webhook创建成功
Webhook URL: https://xxx.execute-api.us-east-1.amazonaws.com/prod/codereview
```

---

## 🧪 运行集成测试

### Single 模式测试

测试单文件评审模式，每个修改的文件独立评审。

```bash
# GitHub - Claude 4
python test/integration/test_rule_single.py github --model claude4

# GitHub - Claude 3.7 (Extended Thinking)
python test/integration/test_rule_single.py github --model claude3.7

# GitLab - Claude 4.5
python test/integration/test_rule_single.py gitlab --model claude4.5

# 支持的模型: claude3.5, claude3.7, claude4, claude4.5
```

### All 模式测试

测试整库评审模式，所有代码合在一起评审。

```bash
# GitHub - Claude 4
python test/integration/test_rule_all.py github --model claude4

# GitHub - Claude 3.7
python test/integration/test_rule_all.py github --model claude3.7
```

### 测试输出示例

```
✅ 测试成功：github claude4 Single模式代码评审规则验证通过

Request表:
- task_total: 6
- task_complete: 6
- task_failure: 0
- task_status: Complete

Task表: 6个tasks全部成功
- 所有tasks使用claude4-sonnet模型
- Bedrock调用耗时: 4.7秒 到 11.5秒不等

Report URL: https://aws-cr-1p3-report-xxx.s3.amazonaws.com/...
```

---

## 🐛 常见坑和故障排除

### 🔴 坑 #1: Lambda 环境变量未配置 (最常见！)

**症状**:
- ❌ 401 Unauthorized 错误
- ❌ GitHub authentication failed
- ❌ task_total = 0 (没有创建任务)
- ❌ Required parameter name not set

**原因**:
Lambda 函数 `request-handler` 和 `task-dispatcher` 缺少 `ACCESS_TOKEN` 环境变量

**解决方案**:
```bash
# 1. 检查环境变量
aws lambda get-function-configuration \
  --function-name aws-cr-1p3-request-handler \
  --region us-east-1 \
  --query 'Environment.Variables.ACCESS_TOKEN'

# 2. 如果为空或不存在，配置它
aws lambda update-function-configuration \
  --function-name aws-cr-1p3-request-handler \
  --environment "Variables={ACCESS_TOKEN=ghp_your_token,...}" \
  --region us-east-1
```

**验证**:
- 查看 CloudWatch 日志不再有 401 错误
- Request 表的 task_total > 0

---

### 🔴 坑 #2: Model ID 格式错误

**症状**:
- ❌ `ValidationException: Model not supported with on-demand throughput`
- ❌ Bedrock API 调用失败

**原因**:
Claude 3.7/4/4.5 必须使用 `us.anthropic.xxx` 格式，不能用 `anthropic.xxx`

**正确格式**:
```python
# ❌ 错误
'anthropic.claude-3-7-sonnet-20250219-v1:0'

# ✅ 正确
'us.anthropic.claude-3-7-sonnet-20250219-v1:0'
```

**解决方案**:
使用 `lambda/model_config.py` 中的 `get_model_id()` 函数，会自动返回正确格式。

---

### 🔴 坑 #3: Converse API 消息格式错误

**症状**:
- ❌ `ValidationException: Invalid content type`
- ❌ Extended Thinking 调用失败

**原因**:
Converse API 不接受 `{'type': 'text'}` 格式

**正确格式**:
```python
# ❌ InvokeModel 格式 (错误用在 Converse)
{'type': 'text', 'text': 'message'}

# ✅ Converse 格式
{'text': 'message'}
```

**解决方案**:
在 `task_executor.py` 中已正确处理，无需手动修改。

---

### 🔴 坑 #4: Extended Thinking 参数限制

**症状**:
- ❌ `ValidationException: temperature must be 1.0`
- ❌ `ValidationException: thinking.budget_tokens must be >= 1024`

**原因**:
Extended Thinking 有严格的参数要求

**正确配置**:
```python
{
  "temperature": 1.0,  # 必须是 1.0
  "thinking": {
    "type": "enabled",
    "budget_tokens": 2048  # >= 1024
  },
  "maxTokens": 4096  # > thinking.budget_tokens
}
```

**解决方案**:
在 `task_executor.py` 中已自动处理，确保使用 `model_config.py` 的配置。

---

### 问题 1: ModuleNotFoundError

**错误**: `ModuleNotFoundError: No module named 'model_config'`

**解决方案**: 从项目根目录运行测试，或使用 `scripts/test_local.py`
```bash
cd /path/to/project
python scripts/test_local.py --only model
```

---

### 问题 2: NoCredentialsError (Bedrock 测试)

**错误**: `botocore.exceptions.NoCredentialsError: Unable to locate credentials`

**解决方案**:
- 选项 1: 跳过 Bedrock API 调用
  ```bash
  python scripts/test_local.py --no-bedrock
  ```
- 选项 2: 配置 AWS 凭证
  ```bash
  aws configure
  ```

---

### 问题 3: 测试很慢

**原因**: 实际调用了 Bedrock API

**解决方案**: 使用 `--no-bedrock` 跳过 API 调用
```bash
python scripts/test_local.py --no-bedrock
```

---

### 问题 4: 集成测试失败

**排查步骤**:

1. **检查 Lambda 环境变量** (最重要！):
```bash
aws lambda get-function-configuration \
  --function-name aws-cr-1p3-request-handler \
  --region us-east-1 \
  --query 'Environment.Variables'
```

2. **检查 CloudWatch 日志**:
```bash
aws logs tail /aws/lambda/aws-cr-1p3-lambda-logs \
  --since 10m --format short --region us-east-1
```

查找关键词:
- `ERROR`
- `401` (认证失败)
- `ValidationException`
- `Required parameter`

3. **检查 DynamoDB 数据**:
```bash
# 查看 Request 表
aws dynamodb scan \
  --table-name aws-cr-1p3-request \
  --region us-east-1 \
  --max-items 5
```

4. **检查 Webhook 状态**:
- GitHub: https://github.com/username/repo/settings/hooks
- 查看最近的 deliveries 和响应

---

## 🔬 测试清理和调试

### 测试前清理 CloudWatch 日志

为了方便查看测试日志，建议先清理：

```bash
# 设置项目名称
PROJECT_NAME="aws-cr-1p3"

# 删除 Lambda 日志组
aws logs delete-log-group \
  --log-group-name "/aws/lambda/${PROJECT_NAME}-lambda-logs" \
  --region us-east-1

# 删除 API Gateway 日志组
API_ID=$(aws apigateway get-rest-apis \
  --query "items[?name==\`${PROJECT_NAME}-api\`].id" \
  --output text)
aws logs delete-log-group \
  --log-group-name "API-Gateway-Execution-Logs_${API_ID}/prod" \
  --region us-east-1
```

### 调试技巧

**1. 查看 Lambda 日志**:
```bash
# 实时查看最近10分钟日志
aws logs tail /aws/lambda/aws-cr-1p3-lambda-logs \
  --since 10m --format short --region us-east-1 --follow

# 过滤错误
aws logs tail /aws/lambda/aws-cr-1p3-lambda-logs \
  --since 10m --format short --region us-east-1 | grep ERROR

# 查找特定 commit
aws logs tail /aws/lambda/aws-cr-1p3-lambda-logs \
  --since 30m --format short --region us-east-1 | grep <commit_id>
```

**2. 检查 SQS 队列深度**:
```bash
aws sqs get-queue-attributes \
  --queue-url <queue-url> \
  --attribute-names ApproximateNumberOfMessages \
  --region us-east-1
```

**3. 查看 webhook deliveries (GitHub)**:
```bash
curl -H "Authorization: token <token>" \
  https://api.github.com/repos/<owner>/<repo>/hooks/<hook_id>/deliveries
```

---

## 📚 仿真数据构建 (高级)

### simulation_lib.py 用法

集成测试使用仿真数据模拟真实的代码提交历史。

**核心函数**:

```python
from test.simulation_lib import apply_commits_github, apply_commits_gitlab

# 加载配置
with open('test/test_config.json', 'r') as f:
    config = json.load(f)

# GitHub - 应用前4个commits，使用 Claude 4 规则
commit_id, project_name = apply_commits_github(config, commit_count=4, model='claude4')

# GitLab - 应用所有commits，使用 Claude 3.7 规则
commit_id, project_name = apply_commits_gitlab(config, model='claude3.7')
```

### 规则文件命名规范

所有规则文件采用格式: `<rule-name>-<model>.yaml`

```
simulation-data/2/.codereview/
├── code-simplification-claude3.5.yaml    (mode=single)
├── code-simplification-claude3.7.yaml    (mode=single)
├── code-simplification-claude4.yaml      (mode=single)
├── code-simplification-claude4.5.yaml    (mode=single)
├── database-master-slave-issue-claude3.5.yaml    (mode=all)
├── database-master-slave-issue-claude3.7.yaml    (mode=all)
├── database-master-slave-issue-claude4.yaml      (mode=all)
└── database-master-slave-issue-claude4.5.yaml    (mode=all)
```

**模型过滤机制**:
- `apply_commits_github(config, model='claude4')` 只会提交 `-claude4.yaml` 文件
- 其他模型的规则文件会被自动跳过
- 这样可以针对特定模型进行隔离测试

### SIMULATIONS.yaml 格式

每个仿真提交目录包含 `SIMULATIONS.yaml`:

```yaml
# 必需字段
commit_message: "提交信息描述"

# 可选字段
deletes:
  - "path/to/delete/file1"      # 需要删除的文件路径列表
  - "path/to/delete/file2"
```

### simulation-data/ 目录结构

```
simulation-data/
├── 1/                          # 第1次提交
│   ├── SIMULATIONS.yaml
│   └── .gitignore
├── 2/                          # 第2次提交
│   ├── SIMULATIONS.yaml
│   ├── .codereview/
│   │   ├── code-simplification-claude3.5.yaml
│   │   ├── code-simplification-claude3.7.yaml
│   │   ├── code-simplification-claude4.yaml
│   │   └── ...
│   └── README.md
├── 3/                          # 第3次提交
│   ├── SIMULATIONS.yaml
│   ├── pom.xml
│   └── src/main/java/App.java
└── ...
```

