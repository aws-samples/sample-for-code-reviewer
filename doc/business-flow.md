# 业务流程与配置详情

## 业务流程概览

### 完整业务流程

```
开发者Push/Merge代码
        ↓
GitLab/GitHub/WebTool触发
        ↓
API Gateway接收请求
        ↓
request_handler解析事件
        ↓
读取.codereview/*.yaml规则
        ↓
规则匹配与过滤
        ↓
task_dispatcher创建评审任务
        ↓
SQS队列分发任务
        ↓
task_executor并行执行Bedrock调用
        ↓
生成评审报告
        ↓
SNS通知用户
```

### 评审规则处理

系统通过读取仓库中的 `.codereview/*.yaml` 文件来获取评审规则。当开发者push代码或创建merge request时，webhook事件会触发系统获取当前分支下的所有规则文件，然后根据规则中的 `branch` 和 `event` 字段进行匹配过滤。

**多规则并行处理**：所有匹配分支条件的`.codereview/*.yaml`文件都会被处理，系统会为每个匹配的规则创建独立的评审任务。这些任务并行执行，互不影响，确保不同评审维度都能得到充分检查。

**无优先级设计**：规则独立执行，没有优先级排序。系统不会根据规则文件名、创建时间或其他因素确定执行顺序，所有匹配的规则都具有相同的重要性。这种设计简化了规则管理，避免了复杂的优先级配置。

**结果聚合与冲突处理**：所有规则的评审结果会合并到一个综合HTML报告中。当多个规则对同一代码段提供不同建议时，系统不会自动过滤或合并冲突的建议，而是将所有建议都包含在报告中，供开发者根据具体情况进行决策。

这种设计允许用户为不同的代码模块、不同的评审关注点设置独立的规则，比如可以有专门检查安全问题的规则、专门检查性能问题的规则、专门检查代码风格的规则等，它们可以同时运行并提供各自的评审意见。

## 触发机制

### GitLab配置
- **Webhook URL**: `https://your-api-gateway-url/prod/codereview`
- **触发事件**: Push Events, Merge Request Events
- **Secret Token**: 配置secret会通过header传递access token给server

### GitHub配置
- **Webhook URL**: `https://your-api-gateway-url/prod/codereview`
- **触发事件**: Push Events, Pull Request Events
- **认证方式**: 需要在server上配置环境变量，不需要配置webhook secret

### WebTool手动触发
- **触发方式**: 用户通过Web界面手动指定评审模式和参数
- **参数控制**: 可以直接指定mode、target等参数，不依赖规则文件配置
- **Access Token传递机制**:
  - WebTool请求在POST body的`private_token`字段中传递token值
  - 后端根据`source`参数（从POST body获取）识别仓库类型
  - 后端从POST body的`private_token`字段获取access token进行API调用

### 事件处理流程（通用）

1. **API Gateway接收**: 接收webhook POST请求或WebTool请求，包含代码仓库信息和事件数据
2. **事件解析**: `request_handler` Lambda解析事件并标准化参数
3. **认证处理**: 
   - GitLab Webhook: 使用webhook header中的access token
   - GitHub Webhook: 使用预配置的环境变量中的access token
   - WebTool: 
     - 从POST body的`source`字段识别仓库类型
     - 从POST body的`private_token`字段获取access token
     - 前端自动根据仓库URL或用户选择设置正确的source参数和private_token值
4. **规则获取**: 使用API读取 `.codereview/*.yaml` 规则文件
5. **规则匹配**: 根据分支和事件类型过滤适用规则
6. **代码获取**: 获取代码内容并按target字段过滤文件
7. **任务创建**: 创建Bedrock任务并发送到SQS队列

## 模块化评审配置

系统支持基于目标文件的模块化评审配置。在规则文件中使用`target`字段可以指定文件路径模式，支持标准glob模式（`*`匹配单层目录，`**`匹配多层目录，`?`匹配单个字符）。这种设计允许将大型代码库按模块分解为可管理的评审块，比如可以分别为前端代码、后端API、数据库层等设置不同的评审规则。

## 任务处理与超时机制

系统采用异步任务处理架构。请求处理器接收webhook后在DynamoDB中创建请求记录，任务分发器将请求分解为单个Bedrock任务并通过递增计数器生成任务编号发送到SQS。任务执行器消费SQS消息并支持并行执行，多个Lambda实例可同时处理不同任务。进度检查器持续监控整体请求完成状态。

系统设置15分钟超时机制，通过EventBridge每分钟触发cron函数检查任务状态。超时时间可通过REPORT_TIMEOUT_SECONDS环境变量配置，检查频率可在lib/cron-stack.ts中调整。当任务超时或全部完成时，报告生成器会聚合结果并通过SNS发送通知。失败的任务不会阻塞其他任务完成，超时报告会包含所有已完成任务的结果。

系统还提供实时进度跟踪，通过DynamoDB和`/result` API端点进行状态查询，Web工具每1秒轮询API获取任务状态并实时显示详细信息。

## 重试和错误处理

系统实现了完善的Bedrock重试机制，通过环境变量进行配置：SQS_MAX_RETRIES=5（最大重试次数）、SQS_BASE_DELAY=2（基础延迟秒数）、SQS_MAX_DELAY=60（最大延迟秒数）、MAX_FAILED_TIMES=6（最大失败次数）。系统使用指数退避策略，失败后重新发送到SQS队列进行延迟处理，确保临时性错误能够得到有效恢复。