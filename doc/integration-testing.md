# 集成测试文档

## 概述

集成测试使用真实的 GitHub 和 GitLab 服务器进行端到端测试，验证整个代码评审流程的完整性。测试覆盖从 webhook 触发到最终报告生成的全流程。

**注意**：GitHub和GitLab仓库可以按需选择，不需要同时配置两个平台。

## 环境准备

### 测试前准备

确保以下环境就绪：

1. **网络连接**：
   - 能够访问 GitHub/GitLab API
   - 能够克隆和推送代码到测试仓库

2. **本地依赖**：
   ```bash
   pip install -r test/requirements.txt
   ```

### 1. 代码仓库准备

#### GitHub 仓库（可选）
1. 在 [github.com](https://github.com) 创建测试仓库
2. 建议命名：`account-book` 或其他测试专用名称
3. 确保仓库为公开或有足够权限访问

#### GitLab 仓库（可选）
1. 在 [gitlab.com](https://gitlab.com) 创建测试仓库
2. 建议使用相同的仓库名称保持一致性
3. 确保仓库为公开或有足够权限访问

### 2. Access Token 配置

#### GitHub Personal Access Token（如果使用GitHub）
1. 访问 [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
2. 点击 "Generate new token (classic)"
3. 设置 token 名称：`code-reviewer-test`
4. **必需权限**：
   - ✅ `repo` - 完整仓库访问权限
   - ✅ `admin:repo_hook` - 管理仓库 webhook 权限（可选，通常repo权限已足够）
5. 生成并保存 token

#### GitLab Access Token（如果使用GitLab）
1. 访问 [GitLab Settings > Access Tokens](https://gitlab.com/-/user_settings/personal_access_tokens)
2. 创建新的 Personal Access Token
3. 设置 token 名称：`code-reviewer-test`
4. **必需权限**：
   - ✅ `api` - 完整 API 访问权限
   - ✅ `read_repository` - 读取仓库
   - ✅ `write_repository` - 写入仓库
5. 生成并保存 token

### 3. 测试配置文件

复制并编辑配置文件：

```bash
cp test_config.json.template test_config.json
# 然后编辑 test_config.json 填入实际配置信息
```

配置文件示例：

```json
{
  "github": {
    "url": "https://api.github.com",
    "token": "your_github_token_here",
    "username": "your_username",
    "test_repo": "account-book",
    "project_id": "your_username/account-book",
    "repo_url": "git@github.com:your_username/account-book.git",
    "owner": "your_username",
    "repo_name": "account-book"
  },
  "gitlab": {
    "url": "https://gitlab.com",
    "token": "your_gitlab_token_here",
    "username": "your_username",
    "test_repo": "account-book",
    "project_id": "your_username/account-book",
    "repo_url": "git@gitlab.com:your_username/account-book.git"
  },
  "aws": {
    "endpoint": "https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/prod",
    "request_table": "code-reviewer-demo-request",
    "task_table": "code-reviewer-demo-task",
    "sqs_url": "https://sqs.us-east-1.amazonaws.com/YOUR_ACCOUNT_ID/code-reviewer-demo-queue",
    "task_dispatcher_function": "code-reviewer-demo-task-dispatcher"
  }
}
```

## Webhook 配置

### 第一步：初始化 Webhook（必须）

在运行集成测试之前，必须先配置 webhook。使用自动化脚本：

```bash
# 使用自动化脚本初始化所有webhook
python3 test/init_webhook.py
```

该脚本会：
1. 自动读取 `test_config.json` 配置
2. 验证 API Gateway endpoint 有效性
3. 删除现有的 `/codereview` 结尾的 webhook（避免重复）
4. 为 GitHub 和 GitLab 仓库自动配置新的 webhook
5. 提供详细的成功/失败反馈

### 手动初始化（备选方案）

如果自动化脚本失败，也可以直接在GitHub/GitLab仓库设置页面手动创建webhook。

## 测试前清理（推荐）

为了方便查看测试日志和避免历史数据干扰，建议在运行集成测试前清理CloudWatch日志组：

```bash
# 设置项目名称变量（根据实际部署时的ProjectName参数）
PROJECT_NAME="code-reviewer-demo"

# 删除 Lambda 日志组
aws logs delete-log-group --log-group-name "/aws/lambda/${PROJECT_NAME}-lambda-logs"

# 查询并删除 API Gateway 日志组
API_ID=$(aws apigateway get-rest-apis --query "items[?name==\`${PROJECT_NAME}-api\`].id" --output text)
aws logs delete-log-group --log-group-name "API-Gateway-Execution-Logs_${API_ID}/prod"
```

## 运行集成测试

### Single 模式测试

测试 `.codereview/code-simplification.yaml` 规则的 single 模式评审。
该测试会提交前4个commits，包含多个Java文件，每个文件会产生一个单独的评审任务。

```bash
# GitLab single 模式测试
python3 test/integration/test_rule_single.py gitlab

# GitHub single 模式测试  
python3 test/integration/test_rule_single.py github
```

### All 模式测试

测试整个代码库的 all 模式评审。
该测试会提交所有commits，所有Java文件会汇聚成1个整体评审任务。

```bash
# GitLab all 模式测试
python3 test/integration/test_rule_all.py gitlab

# GitHub all 模式测试
python3 test/integration/test_rule_all.py github
```

## 验证框架

### 两阶段验证机制

1. **初始化阶段验证** (30秒超时)
   - Merge Request 触发后立即开始轮询
   - 监控 Request 表的 `task_total` 字段更新
   - 30秒内完成任务初始化，否则视为失败

2. **执行阶段验证** (5分钟超时)
   - 持续轮询所有 Task 状态变化
   - 对完成的任务执行相应断言
   - 使用标记机制避免重复验证

### 验证数据结构

**Request表验证点**：
- `status`: pending → processing → completed
- `task_total`: 从0更新为实际任务数
- `completed_tasks`: 递增至task_total
- `created_time`: 合理的时间戳

**Task表验证点**：
- `status`: pending → running → completed
- `result`: S3存储路径有效性
- `error_message`: 失败任务的错误信息
- `retry_count`: 重试机制验证

## 仿真数据构建

### 仿真数据构建过程

仿真数据用于创建可重复的测试环境，模拟真实的代码提交历史。构建过程包括：

#### 数据准备步骤
1. **创建提交目录**：在 `simulation-data/` 下按数字顺序创建目录（1, 2, 3...）
2. **配置提交信息**：每个目录包含 `SIMULATIONS.yaml` 配置文件
3. **准备文件变更**：在目录中放置需要提交的文件
4. **应用到仓库**：使用仿真库将数据应用到测试仓库

#### 构建原则
- **真实环境**：使用真实的 GitHub/GitLab 仓库，拒绝 Mock 数据
- **可重复性**：每次运行都能重现相同的提交历史
- **平台兼容**：支持 GitLab 和 GitHub 两种平台
- **增量构建**：支持部分提交应用，便于不同测试场景

### simulation_lib.py 用法

#### 核心函数

**`apply_commits_gitlab(config, commit_count=None)`**
- **功能**：删除并重建 GitLab 仓库的 dev 分支，然后应用仿真数据
- **分支操作**：
  - 通过 GitLab API 删除现有的 dev 分支
  - 基于 main 分支的第一个提交重新创建 dev 分支
  - 在新 dev 分支上按顺序应用仿真提交
- **参数**：
  - `config`: 包含 gitlab 配置的字典
  - `commit_count`: 限制应用的提交数量，None 表示全部
- **返回**：`(commit_id, project_name)` 元组

**`apply_commits_github(config, commit_count=None)`**
- **功能**：删除并重建 GitHub 仓库的 dev 分支，然后应用仿真数据
- **分支操作**：
  - 通过 PyGithub API 删除现有的 dev 分支引用
  - 克隆仓库到本地临时目录
  - 基于 main 分支的第一个提交重新创建 dev 分支
  - 在本地应用所有仿真提交后一次性推送
- **参数**：
  - `config`: 包含 github 配置的字典  
  - `commit_count`: 限制应用的提交数量，None 表示全部
- **返回**：`(commit_id, project_name)` 元组

#### 使用示例

```python
from test.simulation_lib import apply_commits_github, apply_commits_gitlab

# 加载配置
with open('test_config.json', 'r') as f:
    config = json.load(f)

# GitLab - 应用前4个commits
commit_id, project_name = apply_commits_gitlab(config, commit_count=4)

# GitHub - 应用所有commits
commit_id, project_name = apply_commits_github(config)

# GitHub - 应用前10个commits  
commit_id, project_name = apply_commits_github(config, commit_count=10)
```

#### 平台差异处理

**GitLab 实现**：
- 使用 GitLab API 直接操作远程仓库
- 每个变更立即提交到远程分支
- 通过 API 管理分支创建/删除

**GitHub 实现**：
- 克隆到本地临时目录进行 Git 操作
- 本地完成所有提交后一次性推送
- 自动清理临时克隆目录

### SIMULATIONS.yaml 格式

每个仿真提交目录必须包含 `SIMULATIONS.yaml` 配置文件，定义提交的元数据。

#### 基本格式

```yaml
# SIMULATIONS.yaml - 仿真提交配置文件

# 必需字段
commit_message: "提交信息描述"

# 可选字段
deletes: 
  - "path/to/delete/file1"      # 需要删除的文件路径列表
  - "path/to/delete/file2"      # 相对于项目根目录
```

#### 字段说明

- **`commit_message`**：Git 提交信息，必需字段
- **`deletes`**：需要删除的文件路径列表，可选字段
  - 路径相对于项目根目录
  - 文件不存在时不会报错
  - 删除操作在复制新文件之前执行

#### 配置示例

```yaml
# 示例1：简单添加文件
commit_message: "Add git ignore file"
deletes: []

# 示例2：添加项目结构
commit_message: "增加pom.xml和主程序App.java"
deletes: []

# 示例3：重构代码（删除旧文件，添加新文件）
commit_message: "重构用户管理模块"
deletes:
  - "src/main/java/OldUserManager.java"
  - "src/test/java/OldUserManagerTest.java"
```

#### 注意事项

- `SIMULATIONS.yaml` 文件本身不会被复制到目标仓库
- 删除操作先于文件复制执行
- 支持中文提交信息
- 文件路径使用正斜杠分隔符

### simulation-data/ 目录结构

仿真数据按照标准化的目录结构组织，确保测试的一致性和可维护性。

#### 目录组织

```
simulation-data/
├── 1/                          # 第1次提交
│   ├── SIMULATIONS.yaml        # 提交配置
│   └── .gitignore              # 要提交的文件
├── 2/                          # 第2次提交
│   ├── SIMULATIONS.yaml
│   └── README.md
├── 3/                          # 第3次提交
│   ├── SIMULATIONS.yaml
│   ├── pom.xml
│   └── src/
│       └── main/
│           └── java/
│               └── App.java
├── 4/                          # 第4次提交
│   ├── SIMULATIONS.yaml
│   └── src/
│       └── main/
│           └── java/
│               └── UserManager.java
└── ...                         # 更多提交
```

#### 命名规范

- **目录名称**：使用连续的数字命名（1, 2, 3, ...）
- **排序规则**：按数字大小排序，不是字符串排序
- **配置文件**：每个目录必须包含 `SIMULATIONS.yaml`
- **文件结构**：保持与目标项目相同的目录结构

### init_gitlab.py/init_github.py 使用

仓库初始化脚本，调用 simulation_lib 将所有仿真数据应用到测试仓库。

**使用方法**：
```bash
# GitLab 仓库初始化
python test/init_gitlab.py

# GitHub 仓库初始化  
python test/init_github.py
```

**功能**：读取 `test/test_config.json` 配置，调用对应的 `apply_commits_*()` 函数应用所有仿真提交。

**注意**：会删除现有 dev 分支，请确保没有重要数据。
