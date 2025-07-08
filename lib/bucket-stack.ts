import { Construct } from 'constructs';
import { Bucket, BucketEncryption, BlockPublicAccess } from 'aws-cdk-lib/aws-s3';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as lambda from 'aws-cdk-lib/aws-lambda';

export class CRBucket extends Construct {
	public readonly report_bucket: Bucket;
	public readonly asset_bucket: Bucket;
	public readonly report_cdn: cloudfront.Distribution;

	constructor(scope: Construct, id: string, props: { stack_name: string; account: string; region: string; prefix: string }) {
		super(scope, id);

		// 创建访问日志存储桶
		const access_logs_bucket = new Bucket(this, 'AccessLogsBucket', {
			bucketName: `${props.prefix}-logs-${props.account}-${props.region}`,
			encryption: BucketEncryption.S3_MANAGED,
			blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
			enforceSSL: true,
			versioned: true,
		});

		// 创建主要存储桶
		this.report_bucket = new Bucket(this, 'CodeReviewBucket', {
			bucketName: `${props.prefix}-report-${props.account}-${props.region}`,
			encryption: BucketEncryption.S3_MANAGED,
			blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
			enforceSSL: true,
			versioned: true,
			serverAccessLogsBucket: access_logs_bucket,
			serverAccessLogsPrefix: 'logs/',
		})

		new s3deploy.BucketDeployment(this, 'DeployWebToolFiles', {
			sources: [s3deploy.Source.asset('./webtool')],
			destinationBucket: this.report_bucket,
			destinationKeyPrefix: 'webtool/',
		})

		const timestamp = new Date().getTime();
		const cloudfrontFunction = new cloudfront.Function(this, 'CloudFrontFunction', {
			functionName: `CodeReviewerFunction-${props.prefix}-${props.region}`,
			comment: `Cloudfront Function for Code Reviewer`, 
			code: cloudfront.FunctionCode.fromFile({
				filePath: 'lambda/cloudfront_func.js'
			}),
		});

		/* 创建CloudFront */
		this.report_cdn = new cloudfront.Distribution(this, 'CodeReviewDistribution', {
			defaultBehavior: {
				origin: new origins.S3Origin(this.report_bucket),
				viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
				functionAssociations: [
					{
						eventType: cloudfront.FunctionEventType.VIEWER_REQUEST,
						function: cloudfrontFunction,
					},
				],
			},
		});

	}
}