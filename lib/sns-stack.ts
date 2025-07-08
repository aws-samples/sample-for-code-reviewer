import { Construct } from 'constructs';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as subscriptions from 'aws-cdk-lib/aws-sns-subscriptions';

export class CRSns extends Construct {
  public readonly report_topic: sns.Topic;

  constructor(scope: Construct, id: string, props: { prefix: string }) {
    
    super(scope, id);

    this.report_topic = new sns.Topic(this, 'ReportTopic', {
      topicName: `${props.prefix}-topic`,
      fifo: false
    });

  }
}
