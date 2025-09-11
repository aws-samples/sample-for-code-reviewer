# 报告系统

## 概述

Code Reviewer的报告系统负责收集所有评审任务的结果，生成统一的HTML报告，并提供访问机制。报告系统采用模板化设计，支持自定义样式和内容展示。

## 报告生成机制

报告生成在两种情况下触发：所有评审任务执行完成（成功+失败 >= 总数），或者超过15分钟（900秒）未完成的请求自动生成部分报告。每个任务完成后，`task_executor`会调用`task_base.check_request_progress_by_pksk()`检查整体进度，当满足完成条件时，自动调用`report.generate_report_and_notify()`生成报告。

报告生成时首先从DynamoDB Task表查询所有任务，然后收集成功任务的结果。每个评审任务的结果存储在S3的`results/{request_id}/task_{number}.json`路径中，包含规则名称、AI评审结果内容、使用的模型和提示词等信息。系统会遍历所有成功的任务，从S3读取结果文件并聚合成最终的报告数据。

## 模板系统与内容生成

报告使用`lambda/report_template.html`作为基础模板，这是一个完整的HTML文件，包含CSS样式定义、页面结构和JavaScript渲染逻辑。模板中有一个特殊的`<script id="diy">`标签作为动态数据注入点。

报告生成时，系统会读取模板文件，准备项目名称、当前时间等变量，然后将收集到的评审数据转换为JSON格式。通过正则表达式替换，将数据注入到模板的JavaScript部分，生成包含实际数据的完整HTML文件。最终的报告支持折叠展开显示、语法高亮、响应式设计和打印输出等特性。

## 存储与访问

生成的HTML报告存储在S3中，路径结构为`report/{project_name}/{commit_id}/index.html`。项目名称会被清理，只保留字母数字和下划线。文件上传时设置正确的Content-Type为`text/html`。

报告通过S3预签名URL提供访问，有效期为5天。生成预签名URL后，系统会更新DynamoDB Request表，记录报告的S3路径、访问URL和完成状态。用户可以通过API `/result`接口查询报告状态和获取访问链接。

## 通知与故障处理

报告生成完成后，系统会发送SNS消息，包含报告标题、生成时间、访问URL等信息。SNS消息由`report_receiver` Lambda处理，通过SMTP发送邮件通知到配置的收件人。

当部分任务失败时，系统仍会生成包含成功任务结果的报告，确保用户能获得可用的评审结果。报告生成失败时会记录错误日志，但不会自动重试。预签名URL过期后，用户需要重新通过API获取新的访问链接。

## 自定义配置

用户可以通过修改`lambda/report_template.html`自定义报告的样式、布局和交互功能。超时时间通过环境变量`REPORT_TIMEOUT_SECONDS`配置（默认900秒），S3存储桶通过`BUCKET_NAME`指定。邮件通知的收件人通过`ReportReceiver`环境变量配置。
