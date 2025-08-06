# 数据结构与事件流转

## 概述

本文档详细描述了Code Reviewer系统中几个核心概念的数据结构和属性，包括Webhook事件、规则属性、系统参数和任务结构。理解这些数据结构对于开发、测试和维护系统至关重要。

## 1. Webhook Event（Webhook事件）

### GitLab Push Event
GitLab发送的Push事件原始结构：

```json
{
  "object_kind": "push",
  "event_name": "push",
  "before": "previous_commit_id",
  "after": "current_commit_id", 
  "ref": "refs/heads/branch_name",
  "user_username": "username",
  "project": {
    "id": 123,
    "name": "project_name",
    "path_with_namespace": "group/project",
    "web_url": "https://gitlab.example.com/group/project"
  }
}
```

**关键属性说明**：
- `object_kind`: 事件类型，值为 `"push"`
- `before`: 推送前的提交ID（previous_commit_id）
- `after`: 推送后的提交ID（current_commit_id）
- `ref`: 完整的分支引用，格式为 `"refs/heads/branch_name"`
- `user_username`: 触发推送的用户名
- `project`: 项目信息对象

### GitLab Merge Request Event
GitLab发送的Merge Request事件原始结构：

```json
{
  "object_kind": "merge_request",
  "event_type": "merge_request",
  "user": {
    "username": "username"
  },
  "object_attributes": {
    "target_branch": "main",
    "source_branch": "feature_branch", 
    "merge_status": "checking",
    "last_commit": {
      "id": "commit_id"
    }
  },
  "project": {
    "id": 123,
    "name": "project_name",
    "path_with_namespace": "group/project",
    "web_url": "https://gitlab.example.com/group/project"
  }
}
```

**关键属性说明**：
- `object_kind`: 事件类型，值为 `"merge_request"`
- `object_attributes.target_branch`: 合并目标分支
- `object_attributes.source_branch`: 合并源分支
- `object_attributes.merge_status`: 合并状态，只有 `"checking"` 状态才会触发评审
- `object_attributes.last_commit.id`: 最新提交ID
- `user.username`: 创建合并请求的用户名

## 2. System Parameters（系统参数）

系统内部处理时的标准化参数结构（由 `parse_webtool_parameters` 函数生成）：

```python
params = {
    # 基础信息
    'source': 'gitlab',                    # 代码仓库来源
    'web_url': 'https://gitlab.example.com/group/project',
    'project_id': 123,                     # 项目ID（数字）或 path_with_namespace（字符串）
    'project_name': 'project_name',        # 项目名称
    'repo_url': 'https://gitlab.example.com/',  # 仓库根URL
    'private_token': 'gitlab_token',       # GitLab访问令牌
    'target_branch': 'main',               # 目标分支名（已去除refs/heads/前缀）
    
    # 事件信息（重要：事件类型转换）
    'event_type': 'push',                  # 标准化事件类型：'push' 或 'merge'
    
    # Push事件特有属性
    'commit_id': 'current_commit_id',      # 当前提交ID
    'previous_commit_id': 'previous_commit_id',  # 前一个提交ID
    'ref': 'refs/heads/branch_name',       # 完整分支引用
    'username': 'username',                # 用户名
    
    # Merge Request事件特有属性（当event_type='merge'时）
    # 注意：merge_request事件的event_type会被转换为'merge'
}
```

**重要转换逻辑**：
- **GitLab Webhook** 发送 `merge_request` 事件
- **系统内部处理** 将 `merge_request` 转换为 `merge`
- **规则匹配** 使用转换后的 `merge` 事件类型

**事件类型转换表**：
| GitLab Webhook | 系统内部 | 规则文件中的event |
|----------------|----------|-------------------|
| `push` | `push` | `push` |
| `merge_request` | `merge` | `merge` |

## 3. Rule Attributes（规则属性）

评审规则文件（`.codereview/*.yaml`）的完整属性结构：

```yaml
# 基础配置
name: "规则名称"                    # 规则显示名称
mode: "diff"                      # 评审模式：diff/single/all
branch: "main"                    # 适用分支模式（支持正则表达式）
event: "merge"                    # 触发事件：push/merge
target: "**/*.java"               # 目标文件模式（glob格式）
model: "claude3-sonnet"           # AI模型：claude3-opus/sonnet/haiku

# 提示词配置
system: |                         # 系统提示词（可选）
  You are an experienced developer...
  
# 自定义字段（可扩展）
business: |                       # 业务描述
  项目业务逻辑说明...
  
design: |                         # 设计说明
  架构设计要求...
  
requirement: |                    # 需求说明
  具体评审要求...
  
# 其他自定义字段
confirm: false                    # 是否需要确认
order: "system,business,design"   # 字段处理顺序
```

**核心属性说明**：
- `name`: 规则的显示名称，用于日志和报告
- `mode`: 评审模式，决定评审范围
  - `diff`: 只评审变更的文件
  - `single`: 逐个文件评审
  - `all`: 评审整个代码库
- `branch`: 分支匹配模式，支持正则表达式
- `event`: 触发事件类型，必须是 `push` 或 `merge`
- `target`: 文件匹配模式，使用glob语法
- `model`: 使用的AI模型版本

**扩展属性**：
- 规则文件支持任意自定义字段
- 自定义字段会作为模板变量传递给AI模型
- 通过 `{{field_name}}` 语法在提示词中引用

## 4. Task Structure（任务结构）

系统内部任务的数据结构：

```python
task = {
    # 任务标识
    'request_id': 'uuid_string',          # 请求唯一标识
    'number': 1,                          # 任务序号（数字类型）
    'commit_id': 'commit_hash',           # 提交ID
    
    # 任务配置
    'mode': 'diff',                       # 评审模式
    'model': 'claude3-sonnet',            # AI模型
    'rule_name': '规则名称',               # 规则名称
    
    # 执行状态
    'status': 'pending',                  # 任务状态：pending/running/completed/failed
    'created_time': '2024-01-01T00:00:00Z',  # 创建时间
    'updated_time': '2024-01-01T00:00:00Z',  # 更新时间
    
    # 执行内容
    'prompt_system': 'system prompt...',  # 系统提示词
    'prompt_user': 'user prompt...',      # 用户提示词
    'payload': 'code content...',         # 代码内容
    
    # 执行结果
    'data': 's3://bucket/key',            # 结果存储位置（S3 key）
    'result': 'AI response...',           # AI响应结果（可选，用于缓存）
    'error_message': 'error details',     # 错误信息（失败时）
    
    # 重试机制
    'retry_count': 0,                     # 重试次数
    'failed_times': 0,                    # 失败次数
    'need_retry': false                   # 是否需要重试
}
```

**任务状态流转**：
```
pending → running → completed
    ↓         ↓
  failed ← failed (with retry)
```

**存储位置**：
- **DynamoDB Task表**: 任务元数据和状态
- **S3存储桶**: 任务执行结果（JSON格式）
- **SQS队列**: 待执行任务消息

## 5. Request Structure（请求结构）

评审请求的数据结构：

```python
request = {
    # 请求标识（DynamoDB主键）
    'commit_id': 'commit_hash',           # 分区键
    'request_id': 'uuid_string',          # 排序键
    
    # 请求信息
    'project_name': 'project_name',       # 项目名称
    'target_branch': 'main',              # 目标分支
    'event_type': 'push',                 # 事件类型
    'username': 'username',               # 触发用户
    'invoker': 'webhook',                 # 调用来源：webhook/webtool
    
    # 状态管理
    'status': 'pending',                  # 请求状态：pending/processing/completed/timeout
    'created_time': '2024-01-01T00:00:00Z',  # 创建时间
    'updated_time': '2024-01-01T00:00:00Z',  # 更新时间
    
    # 任务统计
    'total_tasks': 5,                     # 总任务数
    'completed_tasks': 3,                 # 已完成任务数
    'failed_tasks': 1,                    # 失败任务数
    
    # 结果信息
    'report_url': 'https://s3.../report.html',  # 报告URL
    'notification_sent': true             # 是否已发送通知
}
```

## 6. 数据流转关系

```
GitLab Webhook Event
        ↓
System Parameters (parse_webtool_parameters)
        ↓
Request Record (DynamoDB)
        ↓
Rule Matching & Task Creation
        ↓
Task Records (DynamoDB) + SQS Messages
        ↓
Task Execution (Lambda)
        ↓
Task Results (S3) + Status Update (DynamoDB)
        ↓
Progress Checking & Report Generation
        ↓
Final Report (S3) + Notification (SNS)
```

## 7. 关键设计原则

### 事件类型标准化
- 外部事件（GitLab）使用原生名称：`push`, `merge_request`
- 内部处理统一转换：`push`, `merge`
- 规则配置使用内部名称：`push`, `merge`

### 数据一致性
- 使用UUID确保请求唯一性
- 使用递增序号确保任务唯一性
- 通过DynamoDB事务确保状态一致性

### 扩展性设计
- 规则文件支持任意自定义字段
- 参数结构预留扩展空间
- 支持多种代码仓库来源（当前仅GitLab）

### 错误处理
- 每个层级都有完整的错误信息记录
- 支持任务级别的重试机制
- 提供详细的日志追踪能力

这些数据结构构成了Code Reviewer系统的核心数据模型，理解它们对于系统的开发、测试、调试和维护都至关重要。