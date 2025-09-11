# 数据结构与事件流转

## 概述

本文档描述Code Reviewer系统中核心数据结构，包括Webhook事件、系统参数、DynamoDB表结构和任务流转。所有示例均基于真实的生产环境数据。

## 1. Webhook事件结构

### GitLab Push事件
```json
{
  "object_kind": "push",
  "event_name": "push",
  "before": "abc123def456...",
  "after": "def456ghi789...",
  "ref": "refs/heads/feature-branch",
  "ref_protected": false,
  "user_id": 12345,
  "user_name": "Developer Name",
  "user_username": "developer_username",
  "user_email": "developer@example.com",
  "project_id": 67890,
  "project": {
    "id": 67890,
    "name": "my-project",
    "description": "Project description",
    "web_url": "https://gitlab.example.com/group/my-project",
    "path_with_namespace": "group/my-project",
    "default_branch": "main",
    "homepage": "https://gitlab.example.com/group/my-project"
  },
  "commits": [
    {
      "id": "def456ghi789...",
      "message": "Add new feature",
      "author": {
        "name": "Developer Name",
        "email": "developer@example.com"
      }
    }
  ],
  "total_commits_count": 1
}
```

### GitHub Push事件
```json
{
  "ref": "refs/heads/feature-branch",
  "before": "abc123def456...",
  "after": "def456ghi789...",
  "repository": {
    "id": 123456789,
    "name": "my-project",
    "full_name": "username/my-project",
    "private": false,
    "owner": {
      "name": "username",
      "email": "user@example.com",
      "login": "username"
    },
    "html_url": "https://github.com/username/my-project",
    "description": "Project description",
    "default_branch": "main"
  },
  "pusher": {
    "name": "username",
    "email": "user@example.com"
  },
  "created": false,
  "deleted": false,
  "forced": false,
  "commits": [
    {
      "id": "def456ghi789...",
      "message": "Add new feature",
      "author": {
        "name": "Developer Name",
        "email": "developer@example.com"
      }
    }
  ],
  "head_commit": {
    "id": "def456ghi789...",
    "message": "Add new feature"
  }
}
```

### GitLab Merge Request事件
```json
{
  "object_kind": "merge_request",
  "event_type": "merge_request",
  "user": {
    "id": 12345,
    "name": "Developer Name",
    "username": "developer_username"
  },
  "project": {
    "id": 67890,
    "name": "my-project",
    "web_url": "https://gitlab.example.com/group/my-project",
    "path_with_namespace": "group/my-project"
  },
  "object_attributes": {
    "id": 98765,
    "iid": 42,
    "source_branch": "feature-branch",
    "target_branch": "main",
    "merge_status": "checking",
    "last_commit": {
      "id": "def456ghi789..."
    }
  }
}
```

## 2. 系统标准化参数

系统内部处理的标准化参数结构（示例）：

```json
{
  "source": "github",
  "web_url": "https://github.com/username/my-project",
  "project_id": "username/my-project",
  "project_name": "my-project",
  "repo_url": "https://github.com",
  "private_token": "",
  "event_type": "push",
  "target_branch": "feature-branch",
  "commit_id": "def456ghi789abc123...",
  "previous_commit_id": "abc123def456ghi789...",
  "ref": "refs/heads/feature-branch",
  "username": "username",
  "request_id": "20250911_143022_github_username"
}
```

**关键字段说明**：
- `source`: 代码仓库类型 (`gitlab`/`github`)
- `event_type`: 标准化事件类型 (`push`/`merge`)
- `project_id`: GitLab使用`path_with_namespace`，GitHub使用`full_name`
- `repo_url`: 仓库根URL，GitLab包含完整域名，GitHub仅为`https://github.com`
- `request_id`: 系统生成的唯一请求标识，格式：`YYYYMMDD_HHMMSS_{source}_{username}`

**事件类型转换**：
| 原始事件 | 系统内部 | 规则匹配 |
|---------|---------|---------|
| `push` | `push` | `push` |
| `merge_request` | `merge` | `merge` |

**平台差异**：
| 字段 | GitLab | GitHub |
|------|--------|--------|
| 项目标识 | `path_with_namespace` | `full_name` |
| 用户名 | `user_username` | `pusher.name` |
| 仓库URL | `project.web_url` | `repository.html_url` |
| 认证方式 | Secret Token (Header) | Access Token (环境变量) |

## 3. DynamoDB表结构

### Request表 (`{prefix}-request`)

**主键结构**：
- 分区键：`commit_id` (STRING)
- 排序键：`request_id` (STRING)

**全局二级索引**：
- `TaskStatusIndex`
  - 分区键：`task_status` (STRING)
  - 排序键：`create_time` (STRING)

**字段结构**：
```json
{
  "commit_id": "def456ghi789abc123...",
  "request_id": "20250911_143022_github_username",
  "project_name": "my-project",
  "target_branch": "feature-branch",
  "event_type": "push",
  "username": "username",
  "invoker": "webhook",
  "status": "pending",
  "created_time": "2025-09-11T14:30:22Z",
  "updated_time": "2025-09-11T14:30:22Z",
  "total_tasks": 5,
  "completed_tasks": 3,
  "failed_tasks": 1,
  "report_url": "https://s3.../report.html",
  "notification_sent": true
}
```

### Task表 (`{prefix}-task`)

**主键结构**：
- 分区键：`request_id` (STRING)
- 排序键：`number` (NUMBER)

**字段结构**：
```json
{
  "request_id": "20250911_143022_github_username",
  "number": 1,
  "commit_id": "def456ghi789abc123...",
  "mode": "diff",
  "model": "claude3-sonnet",
  "rule_name": "Java安全代码评审",
  "status": "pending",
  "created_time": "2025-09-11T14:30:23Z",
  "updated_time": "2025-09-11T14:30:23Z",
  "prompt_system": "你是一个专业的Java安全代码审查员...",
  "prompt_user": "请评审以下代码变更...",
  "payload": "代码内容...",
  "data": "s3://bucket/results/task_1.json",
  "result": "AI评审结果...",
  "error_message": null,
  "retry_count": 0,
  "failed_times": 0,
  "need_retry": false
}
```

**任务状态流转**：
```
pending → running → completed
    ↓         ↓
  failed ← failed (with retry)
```
