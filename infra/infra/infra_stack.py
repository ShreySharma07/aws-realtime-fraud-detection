import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_s3_assets as s3_assets,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_sagemaker as sagemaker,
    aws_apigatewayv2,
    aws_apigatewayv2_integrations,
    aws_dynamodb as dynamodb
)
from constructs import Construct
import os

# GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY',"")

class InfraStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        #Creating AWSDynamoDB Table for feedback and prediction
        predictions_table = dynamodb.Table(self, "FraudPredictionTable",
            partition_key = dynamodb.Attribute(name='predictionID', type=dynamodb.AttributeType.STRING),
            billing_mode = dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy = cdk.RemovalPolicy.DESTROY)

        # 1. Upload the packaged model to S3 as a CDK Asset
        model_asset = s3_assets.Asset(self, "SageMakerModelAsset",
            path=os.path.join(os.getcwd(), "..", "model.tar.gz")
        )

        # 2. Define the SageMaker Execution Role with comprehensive permissions
        sagemaker_role = iam.Role(self, "SageMakerExecutionRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess")
            ],
            inline_policies={
                "SageMakerModelAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "s3:GetObject",
                                "s3:ListBucket",
                                "s3:GetBucketLocation"
                            ],
                            resources=["*"]
                        ),
                        iam.PolicyStatement(
                            actions=[
                                "ecr:GetDownloadUrlForLayer",
                                "ecr:BatchGetImage",
                                "ecr:BatchCheckLayerAvailability",
                                "ecr:GetAuthorizationToken"
                            ],
                            resources=["*"]
                        )
                    ]
                )
            }
        )

        # 5. Use the correct SageMaker XGBoost container URI for ap-south-1
        image_uri = "720646828776.dkr.ecr.ap-south-1.amazonaws.com/sagemaker-xgboost:1.7-1"

        # 6. Define the SageMaker Model
        sagemaker_model = sagemaker.CfnModel(self, "SageMakerCfnModel",
            execution_role_arn=sagemaker_role.role_arn,
            primary_container=sagemaker.CfnModel.ContainerDefinitionProperty(
                image=image_uri,
                model_data_url=model_asset.s3_object_url
            )
        )
        sagemaker_model.node.add_dependency(model_asset)

        # 7. Define the SageMaker Endpoint Configuration
        endpoint_config = sagemaker.CfnEndpointConfig(self, "SageMakerEndpointConfig",
            production_variants=[sagemaker.CfnEndpointConfig.ProductionVariantProperty(
                initial_instance_count=1,
                instance_type="ml.t2.medium",
                model_name=sagemaker_model.attr_model_name,
                variant_name="AllTraffic"
            )]
        )

        # 8. Create the SageMaker Endpoint
        sagemaker_endpoint = sagemaker.CfnEndpoint(self, "SageMakerEndpoint",
            endpoint_config_name=endpoint_config.attr_endpoint_config_name,
            endpoint_name="fraud-detection-endpoint"
        )

        # 9. Define the Proxy Lambda Function
        proxy_lambda = _lambda.Function(self, "ProxyLambda",
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler="lambda_function.handler",
            code=_lambda.Code.from_asset(os.path.join(os.getcwd(), "..", "src")),
            timeout=cdk.Duration.seconds(30),
            environment={
                "SAGEMAKER_ENDPOINT_NAME": sagemaker_endpoint.endpoint_name,
                "GEMINI_API_KEY": self.node.try_get_context('GEMINI_API_KEY') or "",
                "PREDICTIONS_TABLE_NAME": predictions_table.table_name
            }
        )
        proxy_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["sagemaker:InvokeEndpoint"],
            resources=[sagemaker_endpoint.ref]
        ))
        
        # Grant Lambda permission to write to DynamoDB
        predictions_table.grant_read_write_data(proxy_lambda)

        #Feedback Handler Lambda Function
        feedback_lambda = _lambda.Function(self, "FeedbackLambda",
            runtime = _lambda.Runtime.PYTHON_3_8,
            handler = "feedback_handler.handler",
            code = _lambda.Code.from_asset(os.path.join(os.getcwd(), "..", "src")),
            timeout = cdk.Duration.seconds(30),
            environment={
                "PREDICTIONS_TABLE_NAME": predictions_table.table_name
            })
        
        predictions_table.grant_read_write_data(feedback_lambda)

        # 10. Define the API Gateway
        http_api = aws_apigatewayv2.HttpApi(self, "FraudDetectionApi")
        lambda_integration = aws_apigatewayv2_integrations.HttpLambdaIntegration("LambdaIntegration", proxy_lambda)
        http_api.add_routes(
            path="/",
            methods=[aws_apigatewayv2.HttpMethod.POST],
            integration=lambda_integration
        )

        #Integration for the feedback endpoint (/feedback)
        feedback_integration = aws_apigatewayv2_integrations.HttpLambdaIntegration("FeedbackIntegration", feedback_lambda)
        http_api.add_routes(
            path="/feedback",
            methods=[aws_apigatewayv2.HttpMethod.POST],
            integration=feedback_integration
        )

        # 11. Output the API URL
        cdk.CfnOutput(self, "ApiEndpointUrl", value=http_api.url)
        cdk.CfnOutput(self, "PredictionsTableName", value=predictions_table.table_name)