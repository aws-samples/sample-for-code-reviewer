import { Duration, Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as sqs from 'aws-cdk-lib/aws-sqs';

export class CRSqs extends Construct {

  public readonly task_queue: sqs.Queue;

  constructor(scope: Construct, id: string, props: { prefix: string }) {
	  super(scope, id);

    this.task_queue = new sqs.Queue(this, `TaskQueue`, {
      queueName: `${props.prefix}-queue`,
      visibilityTimeout: Duration.minutes(20),
      encryption: sqs.QueueEncryption.KMS_MANAGED,
    })
    
  }
}
