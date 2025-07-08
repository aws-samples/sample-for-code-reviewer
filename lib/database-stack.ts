import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as cfnres from 'aws-cdk-lib/aws-cloudfront';


export class CRDatabase extends Construct {
  
	public readonly request_table: dynamodb.Table;
	public readonly task_table: dynamodb.Table;

	constructor(scope: Construct, id: string, props: { prefix: string }) {
		super(scope, id);

		/*  Request Table */
		this.request_table = new dynamodb.Table(this, 'RequestTable', {
			tableName: `${props.prefix}-request`,
			partitionKey: { name: 'commit_id', type: dynamodb.AttributeType.STRING },
			sortKey: { name: 'request_id', type: dynamodb.AttributeType.STRING},
			billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
			encryption: dynamodb.TableEncryption.AWS_MANAGED,
			stream: dynamodb.StreamViewType.NEW_IMAGE,
			pointInTimeRecovery: true,
		})
		// 添加全局辅助索引
		this.request_table.addGlobalSecondaryIndex({
			indexName: 'TaskStatusIndex',
			partitionKey: { name: 'task_status', type: dynamodb.AttributeType.STRING },
			sortKey: { name: 'create_time', type: dynamodb.AttributeType.STRING },
			projectionType: dynamodb.ProjectionType.ALL,
		});

		/* Task Table */
		this.task_table = new dynamodb.Table(this, 'TaskTable', {
			tableName: `${props.prefix}-task`,
			partitionKey: { name: 'request_id', type: dynamodb.AttributeType.STRING },
			sortKey: { name: 'number', type: dynamodb.AttributeType.NUMBER },
			billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
			encryption: dynamodb.TableEncryption.AWS_MANAGED,
			stream: dynamodb.StreamViewType.NEW_IMAGE,
			pointInTimeRecovery: true,
		})
		
	}

}
