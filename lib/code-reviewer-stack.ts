import * as cdk from 'aws-cdk-lib';
import { SnsEventSource, SqsEventSource } from 'aws-cdk-lib/aws-lambda-event-sources';
import { Construct } from 'constructs';
import { CRBucket  } from './bucket-stack';
import { CRDatabase } from './database-stack';
import { CRSqs } from './sqs-stack';
import { CRSns } from './sns-stack';
import { CRApi } from './api-stack';
import { CRCron } from './cron-stack';
import { addNagSuppressions } from './nag-suppressions';

export class CodeReviewerStack extends cdk.Stack {
	constructor(scope: Construct, id: string, props?: cdk.StackProps) {
		super(scope, id, props);

		const project_name = new cdk.CfnParameter(this, 'ProjectName', {
			type: 'String',
			default: 'aws-code-reviewer',
			description: 'Name of the project. Use only English letters, numbers, hyphens and underscores. All cloud resource names will be prefixed with this. For example, if ProjectName="a-b-c", then the resource prefix will be a-b-c-',
		})
		const prefix = project_name.valueAsString

		const enable_api_key = new cdk.CfnParameter(this, 'EnableApiKey', {
			type: 'String',
			default: 'false',
			allowedValues: [ 'true', 'false', ],
			description: 'Whether to enable the API Key.',
		})
		const api_key_condition = new cdk.CfnCondition(this, 'EnableApiKeyCondition', {
			expression: cdk.Fn.conditionEquals(enable_api_key.valueAsString, 'true')
		});

		// const is_private = new cdk.CfnParameter(this, 'IsPrivate', {
		// 	type: 'String',
		// 	default: 'true',
		// 	allowedValues: [ 'true', 'false', ],
		// 	description: 'TODO',
		// })
		// const private_condition = new cdk.CfnCondition(this, 'PrivateApiGWCondition', {
		// 	expression: cdk.Fn.conditionEquals(is_private.valueAsString, 'true')
		// });

		const smtp_server = new cdk.CfnParameter(this, 'SMTPServer', {
			type: 'String',
			default: '',
			description: '[Optional] SMTP server. If provided, it will be used to send Code Review Report.',
		});
		const smtp_port = new cdk.CfnParameter(this, 'SMTPPort', {
			type: 'String',
			default: '',
			description: '[Optional] SMTP port. If provided, it will be used to send Code Review Report.',
		});
		const smtp_username = new cdk.CfnParameter(this, 'SMTPUsername', {
			type: 'String',
			default: '',
			description: '[Optional] SMTP username. If provided, it will be used to send Code Review Report.',
		});
		const smtp_password = new cdk.CfnParameter(this, 'SMTPPassword', {
			type: 'String',
			default: '',
			description: '[Optional] SMTP password. If provided, it will be used to send Code Review Report.',
		});
		const report_sender = new cdk.CfnParameter(this, 'ReportSender', {
			type: 'String',
			default: '',
			description: '[Optional] Report sender, an email address. If provided, it will be used to send Code Review Report.',
		});
		const report_receiver = new cdk.CfnParameter(this, 'ReportReceiver', {
			type: 'String',
			default: '',
			description: '[Optional] Report receiver, an email address. If provided, it will be used to receive Code Review Report.',
		});

		const bedrock_access_key = new cdk.CfnParameter(this, 'BedrockAccessKey', {
			type: 'String',
			default: '',
			description: '[Optional] Access Key for Bedrock Invoking.',
		});
		const bedrock_secret_key = new cdk.CfnParameter(this, 'BedrockSecretKey', {
			type: 'String',
			default: '',
			description: '[Optional] Secret Key for Bedrock Invoking.',
		});
		const bedrock_region = new cdk.CfnParameter(this, 'BedrockRegion', {
			type: 'String',
			default: '',
			description: '[Optional] Region for Bedrock Invoking.',
		});
		
		const access_token = new cdk.CfnParameter(this, 'AccessToken', {
			type: 'String',
			default: '',
			description: '[Optional] Access token for GitHub/GitLab API access.',
		});

		/* API */
		const api = new CRApi(this, 'API', { 
			prefix: prefix, 
			api_key_condition: api_key_condition, 
		})

		/* Cron */
		const cron = new CRCron(this, 'Cron', { prefix: prefix } )

		/* 创建任务队列SQS */
		const sqs = new CRSqs(this, 'TaskSQS', { prefix: prefix })

		/* 创建Report SNS，并让Emails订阅SNS */
		const sns = new CRSns(this, 'ReportSNS', { prefix: prefix })

		/* 创建必要的S3 Buckets */
		const buckets = new CRBucket(this, 'Buckets', { stack_name: this.stackName, account: this.account, region: this.region, prefix: prefix })

		/* 数据库 */
		const database = new CRDatabase(this, 'Database', { prefix: prefix })

		/* 配置环境变量 */
		api.request_handler.addEnvironment('REQUEST_TABLE', database.request_table.tableName)
		api.request_handler.addEnvironment('TASK_DISPATCHER_FUN_NAME', api.task_dispatcher.functionName)
		api.request_handler.addEnvironment('ACCESS_TOKEN', access_token.valueAsString)

		api.result_checker.addEnvironment('BUCKET_NAME', buckets.report_bucket.bucketName)
		api.result_checker.addEnvironment('REQUEST_TABLE', database.request_table.tableName)
		api.result_checker.addEnvironment('TASK_TABLE', database.task_table.tableName)
		
		api.task_dispatcher.addEnvironment('BUCKET_NAME', buckets.report_bucket.bucketName)
		api.task_dispatcher.addEnvironment('REQUEST_TABLE', database.request_table.tableName)
		api.task_dispatcher.addEnvironment('TASK_TABLE', database.task_table.tableName)
		api.task_dispatcher.addEnvironment('TASK_SQS_URL', sqs.task_queue.queueUrl)
		api.task_dispatcher.addEnvironment('SNS_TOPIC_ARN', sns.report_topic.topicArn)
		api.task_dispatcher.addEnvironment('ACCESS_TOKEN', access_token.valueAsString)

		api.task_executor.addEnvironment('BUCKET_NAME', buckets.report_bucket.bucketName)
		api.task_executor.addEnvironment('REQUEST_TABLE', database.request_table.tableName)
		api.task_executor.addEnvironment('TASK_TABLE', database.task_table.tableName)
		api.task_executor.addEnvironment('TASK_SQS_URL', sqs.task_queue.queueUrl)
		api.task_executor.addEnvironment('SNS_TOPIC_ARN', sns.report_topic.topicArn)
		api.task_executor.addEnvironment('SQS_MAX_RETRIES', '5')
		api.task_executor.addEnvironment('SQS_BASE_DELAY', '2')
		api.task_executor.addEnvironment('SQS_MAX_DELAY', '60')
		api.task_executor.addEnvironment('TEMPERATURE', '0')
		api.task_executor.addEnvironment('TOP_P', '1')
		api.task_executor.addEnvironment('MAX_TOKEN_TO_SAMPLE', '10000')
		api.task_executor.addEnvironment('MAX_FAILED_TIMES', '6')
		api.task_executor.addEnvironment('REPORT_TIMEOUT_SECONDS', '900')
		api.task_executor.addEnvironment('BEDROCK_ACCESS_KEY', bedrock_access_key.valueAsString)
		api.task_executor.addEnvironment('BEDROCK_SECRET_KEY', bedrock_secret_key.valueAsString)
		api.task_executor.addEnvironment('BEDROCK_REGION', bedrock_region.valueAsString)
		api.task_executor.addEnvironment('ACCESS_TOKEN', access_token.valueAsString)

		api.report_receiver.addEnvironment('SMTP_SERVER', smtp_server.valueAsString)
		api.report_receiver.addEnvironment('SMTP_PORT', smtp_port.valueAsString)
		api.report_receiver.addEnvironment('SMTP_USERNAME', smtp_username.valueAsString)
		api.report_receiver.addEnvironment('SMTP_PASSWORD', smtp_password.valueAsString)
		api.report_receiver.addEnvironment('REPORT_SENDER', report_sender.valueAsString)
		api.report_receiver.addEnvironment('REPORT_RECEIVER', report_receiver.valueAsString)

		/* 触发Lambda */
		api.task_executor.addEventSource(new SqsEventSource(sqs.task_queue))
		api.report_receiver.addEventSource(new SnsEventSource(sns.report_topic))

		/* Cron Function */
		cron.cron_func.addEnvironment('BUCKET_NAME', buckets.report_bucket.bucketName)
		cron.cron_func.addEnvironment('REQUEST_TABLE', database.request_table.tableName)
		cron.cron_func.addEnvironment('TASK_TABLE', database.task_table.tableName)
		cron.cron_func.addEnvironment('SNS_TOPIC_ARN', sns.report_topic.topicArn)
		cron.cron_func.addEnvironment('REPORT_TIMEOUT_SECONDS', `900`)

		/* 权限配置 */
		buckets.report_bucket.grantReadWrite(api.task_dispatcher)
		buckets.report_bucket.grantReadWrite(api.task_executor)
		buckets.report_bucket.grantRead(api.result_checker)
		
		database.request_table.grantReadWriteData(api.request_handler)
		database.request_table.grantReadData(api.result_checker)
		database.request_table.grantReadWriteData(api.task_dispatcher)
		database.request_table.grantReadWriteData(api.task_executor)
		database.request_table.grantReadWriteData(cron.cron_func)

		database.task_table.grantReadWriteData(api.task_executor)
		database.task_table.grantReadData(api.task_dispatcher)
		database.task_table.grantReadData(api.result_checker)
		database.task_table.grantReadData(cron.cron_func)
		
		sqs.task_queue.grantSendMessages(api.task_dispatcher)
		sqs.task_queue.grantSendMessages(api.task_executor)
		sqs.task_queue.grantConsumeMessages(api.task_executor)
		
		sns.report_topic.grantPublish(api.task_dispatcher)
		sns.report_topic.grantPublish(api.task_executor)
		sns.report_topic.grantPublish(cron.cron_func)

		/* Output Section */
		new cdk.CfnOutput(this, 'Endpoint', {
			value: `https://${api.api.restApiId}.execute-api.${this.region}.amazonaws.com/prod/codereview`,
			description: 'Endpoint of code reviewer',
		})
		new cdk.CfnOutput(this, 'Web Tool URL', {
			value: `https://${buckets.report_cdn.distributionDomainName}/webtool/index.html`,
			description: 'Web Tool URL of code reviewer',
		});
		
		// 添加 CDK-NAG 抑制规则
		addNagSuppressions(this);
	}

}
