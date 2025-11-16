# 评审规则YAML文件格式

## 概述

评审规则文件位于仓库的 `.codereview/` 目录下，使用YAML格式定义。每个规则文件描述一个独立的评审任务，系统会根据规则中的条件进行匹配和执行。

## 多规则处理机制

系统支持同时处理多个评审规则，具有以下核心特性：

**多规则处理**：所有匹配分支条件的`.codereview/*.yaml`文件都会被处理。系统会扫描整个`.codereview/`目录，对每个规则文件进行分支和事件匹配，符合条件的规则都会创建独立的评审任务。

**无优先级设计**：规则独立执行，没有优先级排序。每个匹配的规则都会并行创建评审任务，不存在规则间的执行顺序或重要性区分。这种设计确保了所有相关的评审维度都能得到充分检查。

**结果聚合**：所有规则结果合并到一个综合报告中。无论有多少个规则被触发，最终都会生成一份统一的HTML报告，包含所有规则的评审结果，便于开发者集中查看和处理。

**冲突解决策略**：当多个规则对同一代码提供不同建议时，所有建议都包含在报告中供用户决策。系统不会自动过滤或合并冲突的建议，而是将决策权交给开发者，让其根据具体情况判断哪些建议更适用。

## 规则文件结构

```yaml
# .codereview/java-security-review.yaml
name: "Java安全代码评审"
mode: "diff"
branch: "main|dev|feature/.*"
event: "push"
target: "**/*.java"
model: "claude3-sonnet"
system: |
  你是一个专业的Java安全代码审查员。
  请重点关注以下安全问题：
  - SQL注入漏洞
  - XSS攻击防护
  - 权限验证缺失
  - 敏感信息泄露
business: |
  这是一个电商平台的后端服务，处理用户订单和支付信息。
  安全性是最高优先级，任何潜在的安全风险都需要指出。
```

## 字段说明

### 必需字段

**name** (string)
- 规则的显示名称，用于日志和报告中标识该规则
- 示例: `"Java代码评审"`, `"前端安全检查"`

**mode** (string)
- 评审模式，决定评审的范围和方式
- 可选值:
  - `diff`: 仅评审提交间变更的文件
  - `single`: 逐个文件分别评审
  - `all`: 评审整个仓库代码库
- 示例: `"diff"`

**branch** (string)
- 分支匹配模式，支持正则表达式
- 只有当前分支匹配此模式时，规则才会被执行
- 示例: `"main"`, `"main|dev"`, `"feature/.*"`

**event** (string)
- 触发事件类型，决定在什么Git事件下执行该规则
- 可选值:
  - `push`: 代码推送事件
  - `merge`: 合并请求事件（GitLab的merge_request，GitHub的pull_request）
- 示例: `"push"`, `"merge"`

**target** (string)
- 目标文件匹配模式，使用glob语法
- 只有匹配此模式的文件才会被包含在评审中
- Glob模式支持: `*`(单层目录), `**`(多层目录), `?`(单个字符)
- 支持逗号分隔的多个模式: `"**/*.java,**/*.kt"`
- 示例: `"**/*.java"`, `"src/main/**/*.ts"`, `"*.py"`

**model** (string)
- 使用的AI模型版本，这是代码中的枚举值，与具体的model ID有映射关系
- 如果有模型变动，需要修改代码支持，因为不同模型的通信格式不同
- 可选值:
  - **Claude 3 系列**: `claude3`, `claude3-haiku`, `claude3-sonnet`, `claude3-opus`
  - **Claude 3.5 系列**: `claude3.5-sonnet`
  - **Claude 3.7 系列**: `claude3.7-sonnet` (支持推理能力)
  - **Claude 4 系列**: `claude4-opus`, `claude4-opus-4.1`, `claude4-sonnet`
  - **Claude 4.5 系列**: `claude4.5-sonnet`, `claude4.5-haiku`
- 示例: `"claude3.5-sonnet"`, `"claude3.7-sonnet"`, `"claude4.5-sonnet"`

### 可选字段

**system** (string, 多行)
- 自定义的系统提示词，用于指导AI的评审行为
- 如果未提供，使用默认的Claude行为
- 支持多行文本，使用YAML的 `|` 语法

**business** (string, 多行)
- 业务背景描述，帮助AI理解代码的业务上下文
- 可以包含项目类型、业务逻辑、特殊要求等信息

**design** (string, 多行)
- 设计要求和架构说明
- 可以包含设计模式、架构原则、技术约束等

**requirement** (string, 多行)
- 具体的评审要求和关注点
- 可以包含代码规范、性能要求、安全标准等

**enable_reasoning** (boolean, 可选)
- 是否启用推理能力 (仅 Claude 3.7 支持)
- 启用后，模型会返回详细的思考过程
- 思考过程会通过 API 返回，但不会在报告中展示(避免报告过长)
- 默认值: `false`
- 示例: `true`

**reasoning_budget** (integer, 可选)
- 推理过程的 token 预算
- 取值范围: 1000-10000
- 默认值: 2000
- 仅在 `enable_reasoning: true` 时有效
- 示例: `3000`

## 事件类型转换

系统内部会对不同平台的事件进行标准化处理：

| 平台 | 原始事件 | 规则中使用 |
|------|----------|------------|
| GitLab | `push` | `push` |
| GitLab | `merge_request` | `merge` |
| GitHub | `push` | `push` |
| GitHub | `pull_request` | `merge` |
