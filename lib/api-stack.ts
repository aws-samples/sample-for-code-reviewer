import * as cdk from 'aws-cdk-lib';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';

import { Construct } from 'constructs';

export class CRApi extends Construct {
	
	public readonly request_handler: lambda.Function
	public readonly result_checker: lambda.Function
	public readonly task_dispatcher: lambda.Function
	public readonly task_executor: lambda.Function
	public readonly rule_loader: lambda.Function
	public readonly rule_updater: lambda.Function
	public readonly report_receiver: lambda.Function
	public readonly api: apigateway.RestApi
	public readonly api_key: apigateway.ApiKey
	public readonly root_resource: apigateway.Resource

	constructor(scope: Construct, id: string, props: { prefix: string; api_key_condition: cdk.CfnCondition }) {
		super(scope, id);

		const layer = new lambda.LayerVersion(this, 'LayerVersion', {
			code: lambda.Code.fromAsset('layer/layer.zip'),
			compatibleRuntimes: [lambda.Runtime.PYTHON_3_13],
			description: 'This layer includes pyyaml, python-gitlab module.',
		})

		const logGroup = new logs.LogGroup(this, 'CodeReviewerLogGroup', {
			logGroupName: `/aws/lambda/${props.prefix}-lambda-logs`,
			retention: logs.RetentionDays.ONE_WEEK,
			removalPolicy: cdk.RemovalPolicy.DESTROY
		})

		/* 处理Request的Lambda */
		this.request_handler = new lambda.Function(this, 'RequestHandler', {
			functionName: `${props.prefix}-request-handler`,
			runtime: lambda.Runtime.PYTHON_3_13,
			code: lambda.Code.fromAsset('lambda'),
			handler: 'request_handler.lambda_handler',
			timeout: cdk.Duration.seconds(30),
			layers: [ layer ],
			loggingFormat: lambda.LoggingFormat.JSON,
			applicationLogLevelV2: lambda.ApplicationLogLevel.INFO,
			logGroup: logGroup
		})

		/* 请求结果的Lambda */
		this.result_checker = new lambda.Function(this, 'ResultChecker', {
			functionName: `${props.prefix}-result-checker`,
			runtime: lambda.Runtime.PYTHON_3_13,
			code: lambda.Code.fromAsset('lambda'),
			handler: 'result_checker.lambda_handler',
			timeout: cdk.Duration.seconds(30),
			layers: [ layer ],
			loggingFormat: lambda.LoggingFormat.JSON,
			applicationLogLevelV2: lambda.ApplicationLogLevel.INFO,
			logGroup: logGroup
		})
		
		/* Bedrock任务分派的Lambda */
		this.task_dispatcher = new lambda.Function(this, 'TaskDispatcher', {
			functionName: `${props.prefix}-task-dispatcher`,
			runtime: lambda.Runtime.PYTHON_3_13,
			code: lambda.Code.fromAsset('lambda'),
			handler: 'task_dispatcher.lambda_handler',
			timeout: cdk.Duration.seconds(60 * 15),
			layers: [ layer ],
			loggingFormat: lambda.LoggingFormat.JSON,
			applicationLogLevelV2: lambda.ApplicationLogLevel.INFO,
			logGroup: logGroup
		})
		this.task_dispatcher.grantInvoke(this.request_handler)

		/* Bedrock任务执行的Lambda */
		this.task_executor = new lambda.Function(this, 'TaskExecutor', {
			functionName: `${props.prefix}-task-executor`,
			runtime: lambda.Runtime.PYTHON_3_13,
			code: lambda.Code.fromAsset('lambda'),
			handler: 'task_executor.lambda_handler',
			timeout: cdk.Duration.seconds(60 * 15),
			layers: [ layer ],
			loggingFormat: lambda.LoggingFormat.JSON,
			applicationLogLevelV2: lambda.ApplicationLogLevel.INFO,
			logGroup: logGroup
		})
		const bedrock_policy = new iam.PolicyStatement({
            actions: ["bedrock:InvokeModel"],
            resources: ["*"],
        })
		this.task_executor.role?.addToPrincipalPolicy(bedrock_policy)

		/* 刷新PE规则的Lambda */
		this.rule_loader = new lambda.Function(this, 'RuleLoader', {
			functionName: `${props.prefix}-rule-loader`,
			runtime: lambda.Runtime.PYTHON_3_13,
			code: lambda.Code.fromAsset('lambda'),
			handler: 'rule_loader.lambda_handler',
			timeout: cdk.Duration.seconds(60),
			layers: [ layer ],
			loggingFormat: lambda.LoggingFormat.JSON,
			applicationLogLevelV2: lambda.ApplicationLogLevel.INFO,
			logGroup: logGroup
		})

		this.rule_updater = new lambda.Function(this, 'RuleUpdater', {
			functionName: `${props.prefix}-rule-updater`,
			runtime: lambda.Runtime.PYTHON_3_13,
			code: lambda.Code.fromAsset('lambda'),
			handler: 'rule_updater.lambda_handler',
			timeout: cdk.Duration.seconds(60),
			layers: [ layer ],
			loggingFormat: lambda.LoggingFormat.JSON,
			applicationLogLevelV2: lambda.ApplicationLogLevel.INFO,
			logGroup: logGroup
		})

		/* 接受报告的Lambda */
		this.report_receiver = new lambda.Function(this, 'ReportReceiver', {
			functionName: `${props.prefix}-report-receiver`,
			runtime: lambda.Runtime.PYTHON_3_13,
			code: lambda.Code.fromAsset('lambda'),
			handler: 'report_receiver.lambda_handler',
			timeout: cdk.Duration.seconds(30),
			layers: [ layer ],
			loggingFormat: lambda.LoggingFormat.JSON,
			applicationLogLevelV2: lambda.ApplicationLogLevel.INFO,
			logGroup: logGroup
		});
		
		/* 创建 API Gateway REST API */
		this.api = new apigateway.RestApi(this, 'API', {
			restApiName: `${props.prefix}-api`,
			description: 'API Gateway for code view',
			endpointConfiguration: {
				types: [ apigateway.EndpointType.REGIONAL ]
			},
			deployOptions: {
				stageName: 'prod',
				loggingLevel: apigateway.MethodLoggingLevel.INFO,
				dataTraceEnabled: true
			},
			cloudWatchRole: true,
			defaultCorsPreflightOptions: {
				allowOrigins: apigateway.Cors.ALL_ORIGINS,
				allowMethods: apigateway.Cors.ALL_METHODS,
				allowHeaders: [ 'Content-Type', 'X-Amz-Date', 'Authorization', 'X-Api-Key', 'X-Amz-Security-Token', 'X-Gitlab-Token' ],
				allowCredentials: true,
				maxAge: cdk.Duration.days(1)
			}
		})
	
		/* 创建 API Gateway 资源和方法 */
		this.root_resource = this.api.root.addResource('codereview')

		/* Code Review POST */
		let method = this.root_resource.addMethod('POST', new apigateway.LambdaIntegration(this.request_handler, { 
			timeout: cdk.Duration.seconds(29) 
		}));
		(method.node.defaultChild as apigateway.CfnMethod).addPropertyOverride('ApiKeyRequired', cdk.Fn.conditionIf(props.api_key_condition.logicalId, true, false))

		/* Result GET */
		method = this.root_resource.addResource('result').addMethod('GET', new apigateway.LambdaIntegration(this.result_checker, { 
			timeout: cdk.Duration.seconds(10) 
		}));
		(method.node.defaultChild as apigateway.CfnMethod).addPropertyOverride('ApiKeyRequired', cdk.Fn.conditionIf(props.api_key_condition.logicalId, true, false))

		/* Refresh Rule GET */
		let rules = this.root_resource.addResource('rules')
		method = rules.addMethod('GET', new apigateway.LambdaIntegration(this.rule_loader, { 
			timeout: cdk.Duration.seconds(29) 
		}));
		(method.node.defaultChild as apigateway.CfnMethod).addPropertyOverride('ApiKeyRequired', cdk.Fn.conditionIf(props.api_key_condition.logicalId, true, false))

		/* Refresh Rule PUT */
		method = rules.addResource('{filename}').addMethod('PUT', new apigateway.LambdaIntegration(this.rule_updater, { 
			timeout: cdk.Duration.seconds(29) 
		}));
		(method.node.defaultChild as apigateway.CfnMethod).addPropertyOverride('ApiKeyRequired', cdk.Fn.conditionIf(props.api_key_condition.logicalId, true, false))

		/* 创建UsagePlan */
		const plan = this.api.addUsagePlan('CodeReviewerUsagePlan', {
			name: `${props.prefix}-usage-plan`,
			throttle: {
			  rateLimit: 100,
			  burstLimit: 100
			}
		})
		plan.addApiStage({
			stage: this.api.deploymentStage,
		})

		/* 创建 API Key */
		this.api_key = new apigateway.ApiKey(this, 'CodeReviewApiKey', {
			apiKeyName: `${props.prefix}-api-key`,
			description: 'API Key for Code Review API'
		})
		const cfn_api_key = this.api_key.node.defaultChild as apigateway.CfnApiKey
		cfn_api_key.cfnOptions.condition = props.api_key_condition

		const cfn_usage_plan_key = new apigateway.CfnUsagePlanKey(this, 'CfnUsagePlanKey', {
			keyId: this.api_key.keyId,
			keyType: 'API_KEY',
			usagePlanId: plan.usagePlanId,
		})
		cfn_usage_plan_key.cfnOptions.condition = props.api_key_condition
		
	}

}
