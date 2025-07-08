# CloudFormation安装法

## 说明

本文介绍如何通过CloudFormation方式安装Code Reviewer方案，如果你只是使用本方案，或者进行简单微调（例如：修改Lambda代码），CloudFormation的安装方法是适合的。

如果适合Code Reviewer项目迭代。如果你需要二次开发Code Reviewer，涉及到架构变更，涉及反复迭代，推荐使用CDK的安装方法，具体可参看《[CDK安装法](INSTALL-CDK.md)》

## 部署CloudFormation

1. 请先登陆AWS Console
2. 点击[Launch the Latest CloudFormation Template](https://console.aws.amazon.com/cloudformation/home#/stacks/new?templateURL=https%3A%2F%2Fcf-template-wengkaer-257712309840-us-east-1.s3.us-east-1.amazonaws.com%2Fcode-reviewer%2Fv1.2.3%2Ftemplate.yaml)进入CloudFormation页面
3. `Create stack`页面，在整个页面右上角选择你希望安装的区域，点击`Next`按钮。
4. `Specify stack details`页面，填写一个Stack name，可随便填写。ProjectName可以保持默认，也可以按需要修改。SMTP等信息按需填写，用于发送代码评审报告，不填写不影响报告产生，但不会收到邮件。点击`Next`按钮。
5. `Configure stack options`页面，保持默认选项。点击`Next`按钮。
6. `Review and create`页面，勾选`I acknowledge that AWS CloudFormation might create IAM resources.`复选框，点击`Submit`按钮。
7. 等待2～3分钟即可完成Stack的安装

⚠️ 注意：目前仅仅支持：美东1（us-east-1）、美西2（us-west-2）、孟买（ap-south-1）、悉尼（ap-southeast-2）、巴黎（eu-west-3）、爱尔兰（eu-west-1）。具体可参看《[按 AWS 地区划分的模型支持](https://docs.aws.amazon.com/zh_cn/bedrock/latest/userguide/models-regions.html)》

⚠️ 注意：如果需要卸载方案，S3 Bucket和DynamoDB不会自动删除，你需要自行删除这些资源。尤其当你需要重新安装方案时，必须先删除已存在的S3 Bucket和DynamoDB表。

**历史版本安装地址**

历史版本信息可参看[CHANGELOG](CHANGELOG.md)：
- [v1.1](https://console.aws.amazon.com/cloudformation/home#/stacks/new?templateURL=https%3A%2F%2Fcf-template-wengkaer-257712309840-us-east-1.s3.us-east-1.amazonaws.com%2Fcode-reviewer%2Fv1.1%2Ftemplate.yaml)
- [v1.0](https://console.aws.amazon.com/cloudformation/home#/stacks/new?templateURL=https%3A%2F%2Fcf-template-wengkaer-257712309840-us-east-1.s3.us-east-1.amazonaws.com%2Fcode-reviewer%2Fv1.0%2Ftemplate.yaml)


## 配置数据库

进入Dynamodb服务，找到数据库表`{project_name}-repository`，已经内置了两条数据。修改这两条数据的repository_url成为你自己的项目的url。你也可以按照你实际需要配置`{project_name}-repository`

> 功能路径：DynamoDB服务 / 左侧菜单Explore items / 右侧过滤栏填写{project_name}


## 配置Gitlab 

**Step1: 找到Endpoint**

首先，在CloudFormation的Output中找到`Endpoint`，记下来备用。

> 功能路径：CloudFormation服务 / 左侧菜单Stacks / 右侧过滤出你创建的Stack / 点击Stack Name进入明细 / Outputs选项卡

**Step2: 找到API Key Value**

在CloudFormation的Output中找到`ApiKeyId`记下来，进入「API Gateway服务」，左侧菜单「API Keys」，找到ID与`ApiKeyId`对应的记录，拷贝API Key这一项，记下来备用。

> 其实，如果你配置了CLI情况下，你也可以通过CloudFormation的Output中找到`HowToGetApiKeyValue`，替换其中`{ApiKeyId}`替换成为`ApiKeyId`的值，在Shell下执行，也可获得API Key Value，记下来备用。

**Step3: 配置AccessToken**

进入Gitlab，按如下表单配置一个Access Token，记下来备用。
```
Role = Reporter
Scope = read_api
```

> 功能路径：Gitlab Project Home / 左侧菜单Settings / Access Tokens / Add new token

**Step4: 配置WebHook**

进入Gitlab，为你的项目创建一个webhook，填写表单如下：
```
URL = Step1中记录的Endpoint
Add custom header
  Header name = X-API-Key
  Header value = Step2中记录的API Key Value
Secret token = Step3中记录的Access Token
Trigger = Push events / All branches + Merge request events (也可以按照需要配置) 
```

> 功能路径：Gitlab Project Home / 左侧菜单Settings / Webhooks / Add new webhook

## 验证

在Gitlab中触发push或者merge request，应该会发生：

日志组`/aws/lambda/{project_name}-request-handler`中应该有以下类似日志输出

  ```
  Received Gitlab event[merge_request]: ...
  The merge status is checking, it is going to invoke code review.
  Parsed code review mode(xx) for branch(xx) by configuration ...
  Complete invoking task dispatcher, payload is ...
  ```

日志组`/aws/lambda/{project_name}-task-dispatcher`中应该有以下类似日志输出

  ```
  Event: ...
  Scaned xx files after ext filtering in repository for commit_id(xx), filters([xx, xx, ...]).
  File content(xx): ...
  Get rules: ...
  Make up new prompt data: ...
  Prepare to send message to SQS(xx): xx
  Succeed to send message to SQS(xx) in base64: xx
  ```

日志组`/aws/lambda/{project_name}-task-executor`中应该有以下类似日志输出

  ```
  Event: ...
  Receiving 1 SQS records: ...
  Plain body: ...
  Task Event: ... 
  Task Context: ... 
  Try to do code review for task(request_id=xx, number=xx)...
  Bedrock - Invoking claude3 for task(request_id=xx, number=xx): ...
  Bedrock - Claude3 replied for task(request_id=xx, number=xx): ...
  Review result is saved in task(request_id=xx, number=xx): ...
  SQS process results: {'batchItemSeccesses': [{'itemIdentifier': 'xx'}], 'batchItemFailures': []}

  Progress Event: ...
  Progress Context: ...
  Checking code review result for request record(commit_id=xx, request_id=xx)...
  Code review is uncomplete. Completes(xx) + Failures(xx) < Total(xx) for request record(commit_id=xx, request_id=xx).
  Mark code review complete. For all sub-task are complete for request record(commit_id=xx, request_id=xx).
  Generating report for request record(commit_id=xx, request_id=xx).
  Report is created to s3://xx/account_book/xx/index.html
  Report URL: ...
  ```

日志组`/aws/lambda/{project_name}-report-receiver`中应该有以下类似日志输出

  ```
  Event: ...
  Got SNS subject: ...
  Got SNS message: ...
  Report is sent to mail xx@xx: ...
  ```

S3 Bucket`{project_name}-report-{account}-{region}`中应该有报告产生

收到代码评审报告邮件
