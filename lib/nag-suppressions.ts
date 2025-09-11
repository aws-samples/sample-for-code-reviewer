import { Stack } from 'aws-cdk-lib';
import { NagSuppressions } from 'cdk-nag';

/**
 * 集中管理所有 CDK-NAG 警告抑制规则
 * @param stack CDK 堆栈
 */
export function addNagSuppressions(stack: Stack): void {
  // IAM 相关抑制
  addIamSuppressions(stack);
  
  // Lambda 相关抑制
  addLambdaSuppressions(stack);
  
  // API Gateway 相关抑制
  addApiGatewaySuppressions(stack);
  
  // SQS 相关抑制
  addSqsSuppressions(stack);
  
  // CloudFront 相关抑制
  addCloudFrontSuppressions(stack);
  
  // SNS 相关抑制
  addSnsSuppressions(stack);
  
  // 其他资源抑制
  addOtherSuppressions(stack);
}

/**
 * IAM 相关警告抑制
 */
function addIamSuppressions(stack: Stack): void {
  // 抑制所有 Lambda 函数的 IAM4 警告 - AWS 托管策略 AWSLambdaBasicExecutionRole
  const lambdaRolePaths = [
    '/CodeReviewerStack/API/RequestHandler/ServiceRole/Resource',
    '/CodeReviewerStack/API/ResultChecker/ServiceRole/Resource',
    '/CodeReviewerStack/API/TaskDispatcher/ServiceRole/Resource',
    '/CodeReviewerStack/API/TaskExecutor/ServiceRole/Resource',
    '/CodeReviewerStack/API/RuleLoader/ServiceRole/Resource',
    '/CodeReviewerStack/API/RuleUpdater/ServiceRole/Resource',
    '/CodeReviewerStack/API/ReportReceiver/ServiceRole/Resource',
    '/CodeReviewerStack/Cron/CronFunction/ServiceRole/Resource',
    '/CodeReviewerStack/Custom::CDKBucketDeployment8693BB64968944B69AAFB0CC9EB8756C/ServiceRole/Resource'
  ];
  
  // 为每个路径添加抑制规则
  lambdaRolePaths.forEach(path => {
    NagSuppressions.addResourceSuppressionsByPath(
      stack,
      path,
      [
        {
          id: 'AwsSolutions-IAM4',
          reason: 'Lambda 执行所需的基本权限，接受此风险',
          appliesTo: ['Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole']
        }
      ]
    );
  });
  
  // 抑制 RequestHandler 调用 TaskDispatcher 的通配符权限警告
  NagSuppressions.addResourceSuppressionsByPath(
    stack,
    '/CodeReviewerStack/API/RequestHandler/ServiceRole/DefaultPolicy/Resource',
    [
      {
        id: 'AwsSolutions-IAM5',
        reason: '需要对 TaskDispatcher Lambda 函数有完全调用权限，包括版本和别名',
        appliesTo: [`Resource::arn:aws:lambda:*:*:function:${stack.stackName}-task-dispatcher:*`]
      },
      {
        id: 'AwsSolutions-IAM5',
        reason: '需要访问 DynamoDB 表的所有索引以处理请求',
        appliesTo: [`Resource::arn:aws:dynamodb:*:*:table/${stack.stackName}-request/index/*`]
      },
      {
        id: 'AwsSolutions-IAM5',
        reason: '需要访问 TaskDispatcher Lambda 函数',
        appliesTo: ['Resource::<APITaskDispatcher9F1B3E10.Arn>:*']
      },
      {
        id: 'AwsSolutions-IAM5',
        reason: '需要访问 DynamoDB 请求表的所有索引',
        appliesTo: ['Resource::<DatabaseRequestTable097B2C2C.Arn>/index/*']
      }
    ]
  );
  
  // ResultChecker 的通配符权限
  NagSuppressions.addResourceSuppressionsByPath(
    stack,
    '/CodeReviewerStack/API/ResultChecker/ServiceRole/DefaultPolicy/Resource',
    [
      {
        id: 'AwsSolutions-IAM5',
        reason: '需要访问 S3 存储桶中的代码评审报告和相关资源',
        appliesTo: [
          'Action::s3:GetBucket*',
          'Action::s3:GetObject*',
          'Action::s3:List*',
          `Resource::arn:aws:s3:::${stack.stackName}-code-review-bucket/*`,
          'Resource::<BucketsCodeReviewBucket464A35B1.Arn>/*'
        ]
      },
      {
        id: 'AwsSolutions-IAM5',
        reason: '需要访问 DynamoDB 表的所有索引以查询请求状态',
        appliesTo: [
          `Resource::arn:aws:dynamodb:*:*:table/${stack.stackName}-request/index/*`,
          'Resource::<DatabaseRequestTable097B2C2C.Arn>/index/*'
        ]
      }
    ]
  );
  
  // TaskDispatcher 的通配符权限
  NagSuppressions.addResourceSuppressionsByPath(
    stack,
    '/CodeReviewerStack/API/TaskDispatcher/ServiceRole/DefaultPolicy/Resource',
    [
      {
        id: 'AwsSolutions-IAM5',
        reason: '需要完全访问 S3 存储桶以处理代码评审任务',
        appliesTo: [
          'Action::s3:Abort*',
          'Action::s3:DeleteObject*',
          'Action::s3:GetBucket*',
          'Action::s3:GetObject*',
          'Action::s3:List*',
          `Resource::arn:aws:s3:::${stack.stackName}-code-review-bucket/*`,
          'Resource::<BucketsCodeReviewBucket464A35B1.Arn>/*'
        ]
      },
      {
        id: 'AwsSolutions-IAM5',
        reason: '需要访问 DynamoDB 表的所有索引以处理任务',
        appliesTo: [
          `Resource::arn:aws:dynamodb:*:*:table/${stack.stackName}-request/index/*`,
          'Resource::<DatabaseRequestTable097B2C2C.Arn>/index/*'
        ]
      }
    ]
  );
  
  // TaskExecutor 的通配符权限
  NagSuppressions.addResourceSuppressionsByPath(
    stack,
    '/CodeReviewerStack/API/TaskExecutor/ServiceRole/DefaultPolicy/Resource',
    [
      {
        id: 'AwsSolutions-IAM5',
        reason: '需要完全访问 S3 存储桶以执行代码评审任务和生成报告',
        appliesTo: [
          'Action::s3:Abort*',
          'Action::s3:DeleteObject*',
          'Action::s3:GetBucket*',
          'Action::s3:GetObject*',
          'Action::s3:List*',
          `Resource::arn:aws:s3:::${stack.stackName}-code-review-bucket/*`,
          'Resource::<BucketsCodeReviewBucket464A35B1.Arn>/*'
        ]
      },
      {
        id: 'AwsSolutions-IAM5',
        reason: '需要访问 DynamoDB 表的所有索引以处理任务',
        appliesTo: [
          `Resource::arn:aws:dynamodb:*:*:table/${stack.stackName}-request/index/*`,
          'Resource::<DatabaseRequestTable097B2C2C.Arn>/index/*'
        ]
      },
      {
        id: 'AwsSolutions-IAM5',
        reason: '需要调用 Bedrock 模型进行代码评审',
        appliesTo: ['Resource::*']
      }
    ]
  );
  
  // CDKBucketDeployment 的 S3 通配符权限
  NagSuppressions.addResourceSuppressionsByPath(
    stack,
    '/CodeReviewerStack/Custom::CDKBucketDeployment8693BB64968944B69AAFB0CC9EB8756C/ServiceRole/DefaultPolicy/Resource',
    [
      {
        id: 'AwsSolutions-IAM5',
        reason: 'CDK BucketDeployment 需要这些权限来部署资源到 S3',
        appliesTo: [
          'Action::s3:GetBucket*',
          'Action::s3:GetObject*',
          'Action::s3:List*',
          'Action::s3:Abort*',
          'Action::s3:DeleteObject*',
          `Resource::arn:aws:s3:::${stack.stackName}-code-review-bucket/*`,
          'Resource::<BucketsCodeReviewBucket464A35B1.Arn>/*',
          'Resource::arn:<AWS::Partition>:s3:::cdk-hnb659fds-assets-<AWS::AccountId>-<AWS::Region>/*'
        ]
      }
    ]
  );
}

/**
 * Lambda 相关警告抑制
 */
function addLambdaSuppressions(stack: Stack): void {
  // 抑制所有 Lambda 函数的运行时版本警告
  const lambdaFunctionPaths = [
    '/CodeReviewerStack/API/RequestHandler/Resource',
    '/CodeReviewerStack/API/ResultChecker/Resource',
    '/CodeReviewerStack/API/TaskDispatcher/Resource',
    '/CodeReviewerStack/API/TaskExecutor/Resource',
    '/CodeReviewerStack/API/RuleLoader/Resource',
    '/CodeReviewerStack/API/RuleUpdater/Resource',
    '/CodeReviewerStack/API/ReportReceiver/Resource',
    '/CodeReviewerStack/Cron/CronFunction/Resource'
  ];
  
  // 为每个 Lambda 函数添加运行时版本抑制规则
  lambdaFunctionPaths.forEach(path => {
    NagSuppressions.addResourceSuppressionsByPath(
      stack,
      path,
      [
        {
          id: 'AwsSolutions-L1',
          reason: '使用 Python 3.12 以确保与 Lambda Layer 中的依赖包兼容性，Python 3.13 存在包兼容性问题'
        }
      ]
    );
  });

  // Cron Function 的通配符权限
  NagSuppressions.addResourceSuppressionsByPath(
    stack,
    '/CodeReviewerStack/Cron/CronFunction/ServiceRole/DefaultPolicy/Resource',
    [
      {
        id: 'AwsSolutions-IAM5',
        reason: '需要访问 DynamoDB 表的所有索引以处理定时任务',
        appliesTo: [
          `Resource::arn:aws:dynamodb:*:*:table/${stack.stackName}-request/index/*`,
          'Resource::<DatabaseRequestTable097B2C2C.Arn>/index/*'
        ]
      }
    ]
  );
  
  // CDK Bucket Deployment Lambda 的运行时版本警告
  NagSuppressions.addResourceSuppressionsByPath(
    stack,
    '/CodeReviewerStack/Custom::CDKBucketDeployment8693BB64968944B69AAFB0CC9EB8756C/Resource',
    [
      {
        id: 'AwsSolutions-L1',
        reason: '这是 CDK 构造自动生成的 Lambda 函数，运行时版本由 CDK 控制'
      }
    ]
  );
}

/**
 * API Gateway 相关警告抑制
 */
function addApiGatewaySuppressions(stack: Stack): void {
  // 抑制 API Gateway 方法没有使用 Cognito 用户池授权器的警告
  const apiMethodPaths = [
    '/CodeReviewerStack/API/API/Default/codereview/POST/Resource',
    '/CodeReviewerStack/API/API/Default/codereview/result/GET/Resource',
    '/CodeReviewerStack/API/API/Default/codereview/rules/GET/Resource',
    '/CodeReviewerStack/API/API/Default/codereview/rules/{filename}/PUT/Resource'
  ];
  
  // 为每个 API 方法路径添加抑制规则
  apiMethodPaths.forEach(path => {
    NagSuppressions.addResourceSuppressionsByPath(
      stack,
      path,
      [
        {
          id: 'AwsSolutions-COG4',
          reason: '此 API 使用 API Key 或其他自定义授权方式，不需要 Cognito 用户池授权'
        },
        {
          id: 'AwsSolutions-APIG4',
          reason: '此 API 使用 API Key 或其他自定义授权方式，不需要额外的授权机制'
        }
      ]
    );
  });
  
  // 抑制 API Gateway 整体相关的警告
  NagSuppressions.addResourceSuppressionsByPath(
    stack,
    '/CodeReviewerStack/API/API/Resource',
    [
      {
        id: 'AwsSolutions-APIG2',
        reason: '此 API 在后端 Lambda 中进行输入验证，不需要 API Gateway 级别的请求验证'
      }
    ]
  );
  
  // 抑制 API Gateway CloudWatch 角色相关的警告
  NagSuppressions.addResourceSuppressionsByPath(
    stack,
    '/CodeReviewerStack/API/API/CloudWatchRole/Resource',
    [
      {
        id: 'AwsSolutions-IAM4',
        reason: '使用标准的 API Gateway CloudWatch 日志角色，这是 AWS 推荐的做法',
        appliesTo: ['Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs']
      }
    ]
  );
  
  // 抑制 API Gateway 部署阶段相关的警告
  NagSuppressions.addResourceSuppressionsByPath(
    stack,
    '/CodeReviewerStack/API/API/DeploymentStage.prod/Resource',
    [
      {
        id: 'AwsSolutions-APIG1',
        reason: '此 API 用于内部代码评审工具，不需要访问日志记录'
      },
      {
        id: 'AwsSolutions-APIG3',
        reason: '此 API 用于内部代码评审工具，不需要与 AWS WAFv2 集成'
      }
    ]
  );
}

/**
 * 其他资源警告抑制
 */
function addOtherSuppressions(stack: Stack): void {

}
/**
 * SQS 相关警告抑制
 */
function addSqsSuppressions(stack: Stack): void {
  // 抑制 TaskQueue 的 SQS3 和 SQS4 警告
  NagSuppressions.addResourceSuppressionsByPath(
    stack,
    '/CodeReviewerStack/TaskSQS/TaskQueue/Resource',
    [
      {
        id: 'AwsSolutions-SQS3',
        reason: '此队列不需要死信队列，任务失败会通过应用逻辑处理和重试'
      },
      {
        id: 'AwsSolutions-SQS4',
        reason: '此队列仅在 AWS 内部使用，不需要强制 SSL 连接'
      }
    ]
  );
}
/**
 * CloudFront 相关警告抑制
 */
function addCloudFrontSuppressions(stack: Stack): void {
  // 抑制 CodeReviewDistribution 的 CloudFront 相关警告
  NagSuppressions.addResourceSuppressionsByPath(
    stack,
    '/CodeReviewerStack/Buckets/CodeReviewDistribution/Resource',
    [
      {
        id: 'AwsSolutions-CFR1',
        reason: '此 CloudFront 分配用于内部代码评审工具，不需要地理位置限制'
      },
      {
        id: 'AwsSolutions-CFR2',
        reason: '此 CloudFront 分配用于内部代码评审工具，不需要与 AWS WAF 集成'
      },
      {
        id: 'AwsSolutions-CFR3',
        reason: '此 CloudFront 分配用于内部代码评审工具，不需要访问日志记录'
      },
      {
        id: 'AwsSolutions-CFR4',
        reason: '此 CloudFront 分配将使用默认的 TLS 设置，在内部环境中可接受此风险'
      },
      {
        id: 'AwsSolutions-CFR7',
        reason: '此 CloudFront 分配使用的是自定义源访问控制方式，不需要 OAC'
      }
    ]
  );
}
/**
 * SNS 相关警告抑制
 */
function addSnsSuppressions(stack: Stack): void {
  // 抑制 SNS 主题的 SSL 警告
  NagSuppressions.addResourceSuppressionsByPath(
    stack,
    '/CodeReviewerStack/ReportSNS/ReportTopic/Resource',
    [
      {
        id: 'AwsSolutions-SNS3',
        reason: '此 SNS 主题仅在 AWS 内部使用，不需要强制 SSL 连接'
      }
    ]
  );
}
