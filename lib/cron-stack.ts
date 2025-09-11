import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';

import { Construct } from 'constructs';

export class CRCron extends Construct {
	
	public readonly cron_func: lambda.Function
	
	constructor(scope: Construct, id: string, props: { prefix: string; }) {
		super(scope, id);
		
		/* 处理进度的Lambda */
		this.cron_func = new lambda.Function(this, 'CronFunction', {
			functionName: `${props.prefix}-cron-function`,
			runtime: lambda.Runtime.PYTHON_3_12,
			code: lambda.Code.fromAsset('lambda'),
			handler: 'cron_function.lambda_handler',
			timeout: cdk.Duration.seconds(30),
		})

		/* EventBridge定时触发的规则 */
		const rule = new events.Rule(this, 'CronRule', {
			schedule: events.Schedule.rate(cdk.Duration.minutes(1)),
		});
		rule.addTarget(new targets.LambdaFunction(this.cron_func));

	}

}
