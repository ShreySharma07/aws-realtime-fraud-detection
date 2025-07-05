from aws_cdk import (
    # Duration,
    #core as cdk,
    Stack,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_apigatewayv2 as apigwv2,
    # aws_sqs as sqs,
)
import os
import aws_cdk as cdk
from constructs import Construct
from aws_cdk.aws_apigatewayv2_integrations import HttpLambdaIntegration

class InfraStack(cdk.Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        # example resource
        # queue = sqs.Queue(
        #     self, "InfraQueue",
        #     visibility_timeout=Duration.seconds(300),
        # )
        model_bucket = s3.Bucket(self, "FraudModeklBucket",
                                 removal_policy = cdk.RemovalPolicy.DESTROY,
                                 auto_delete_objects = True)
        
        #defining lambda our serverless function
        fraud_detection_lambda = _lambda.Function(
            self,
            'FraudDetectionModel',
            runtime = _lambda.Runtime.PYTHON_3_8,
            handler = 'lambda_function.handler',
            code = _lambda.Code.from_asset(os.path.join(os.getcwd(), "..", "src")),
            memory_size = 512,
            timeout = cdk.Duration.seconds(30),
            environment = {
                'MODEL_BUCKET_NAME': model_bucket.bucket_name,
                "MODEL_FILE_KEY": "fraud_detection_model.joblib"
            }
        )

        #grating permission to lambda to read files
        model_bucket.grant_read(fraud_detection_lambda)
        #create a public url to trigger the lambda function
        http_api = apigwv2.HttpApi(
            self,
            'FraudDetectionApi',
            cors_preflight = apigwv2.CorsPreflightOptions(
                allow_headers = ['Content-Type'],
                allow_methods=[apigwv2.CorsHttpMethod.POST, apigwv2.CorsHttpMethod.OPTIONS],
                allow_origins=["*"],
            )
        )

        #creating the integration
        #this connects post request to the apiendpoint /
        lambda_integration = HttpLambdaIntegration(
            "LambdaIntegration",
            fraud_detection_lambda
        )

        http_api.add_routes(
            path="/",
            methods=[apigwv2.HttpMethod.POST],
            integration=lambda_integration
        )

        cdk.CfnOutput(
            self,
            "ModelBucketName",
            value = model_bucket.bucket_name,
            description="The name of the S3 bucket for the fraud detection model."
        )

        cdk.CfnOutput(self, "ApiEndpointUrl",
            value=http_api.url,
            description="The URL of the API Gateway endpoint."
        )