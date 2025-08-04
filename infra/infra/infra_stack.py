

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_s3_assets as s3_assets,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_sagemaker as sagemaker,
    aws_apigatewayv2,
    aws_apigatewayv2_integrations,
    aws_dynamodb as dynamodb,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
    aws_ec2,
)
from constructs import Construct
import os

class InfraStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # --- 1. All Foundational Resources ---
        predictions_table = dynamodb.Table(self, "AuraPredictionsTable",
            partition_key=dynamodb.Attribute(name="predictionId", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=cdk.RemovalPolicy.DESTROY
        )
        training_data_bucket = s3.Bucket(self, "AuraTrainingDataBucket",
            auto_delete_objects=True,
            removal_policy=cdk.RemovalPolicy.DESTROY
        )
        model_asset = s3_assets.Asset(self, "SageMakerModelAsset",
            path=os.path.join(os.getcwd(), "..", "model.tar.gz")
        )
        sagemaker_role = iam.Role(self, "SageMakerExecutionRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess")],
            inline_policies={
                "SageMakerECRAccess": iam.PolicyDocument(statements=[
                    iam.PolicyStatement(actions=["ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage", "ecr:BatchCheckLayerAvailability"], resources=["*"])
                ])
            }
        )
        model_asset.grant_read(sagemaker_role)
        image_uri = "720646828776.dkr.ecr.ap-south-1.amazonaws.com/sagemaker-xgboost:1.7-1"
        sagemaker_model = sagemaker.CfnModel(self, "SageMakerCfnModel",
            execution_role_arn=sagemaker_role.role_arn,
            primary_container=sagemaker.CfnModel.ContainerDefinitionProperty(
                image=image_uri, model_data_url=model_asset.s3_object_url
            )
        )
        endpoint_config = sagemaker.CfnEndpointConfig(self, "SageMakerEndpointConfig",
            production_variants=[sagemaker.CfnEndpointConfig.ProductionVariantProperty(
                initial_instance_count=1, instance_type="ml.t2.medium",
                model_name=sagemaker_model.attr_model_name, variant_name="AllTraffic"
            )]
        )
        sagemaker_endpoint = sagemaker.CfnEndpoint(self, "SageMakerEndpoint",
            endpoint_config_name=endpoint_config.attr_endpoint_config_name,
            endpoint_name="fraud-detection-endpoint"
        )
        proxy_lambda = _lambda.Function(self, "ProxyLambda", runtime=_lambda.Runtime.PYTHON_3_8, handler="lambda_function.handler", code=_lambda.Code.from_asset(os.path.join(os.getcwd(), "..", "src")),
            timeout=cdk.Duration.seconds(30), environment={"SAGEMAKER_ENDPOINT_NAME": sagemaker_endpoint.endpoint_name, "GEMINI_API_KEY": self.node.try_get_context("GEMINI_API_KEY") or "", "PREDICTIONS_TABLE_NAME": predictions_table.table_name})
        predictions_table.grant_read_write_data(proxy_lambda)
        proxy_lambda.add_to_role_policy(iam.PolicyStatement(actions=["sagemaker:InvokeEndpoint"], resources=[sagemaker_endpoint.ref]))
        
        feedback_lambda = _lambda.Function(self, "FeedbackLambda", runtime=_lambda.Runtime.PYTHON_3_8, handler="feedback_handler.handler", code=_lambda.Code.from_asset(os.path.join(os.getcwd(), "..", "src")),
            timeout=cdk.Duration.seconds(30), environment={"PREDICTIONS_TABLE_NAME": predictions_table.table_name})
        predictions_table.grant_read_write_data(feedback_lambda)
        
        export_data_lambda = _lambda.Function(self, "ExportDataLambda", runtime=_lambda.Runtime.PYTHON_3_8, handler="export_data.handler", code=_lambda.Code.from_asset(os.path.join(os.getcwd(), "..", "src")),
            timeout=cdk.Duration.seconds(60), memory_size=256, environment={"PREDICTIONS_TABLE_NAME": predictions_table.table_name, "TRAINING_DATA_BUCKET_NAME": training_data_bucket.bucket_name})
        predictions_table.grant_read_data(export_data_lambda)
        training_data_bucket.grant_write(export_data_lambda)
        
        http_api = aws_apigatewayv2.HttpApi(self, "FraudDetectionApi")
        prediction_integration = aws_apigatewayv2_integrations.HttpLambdaIntegration("PredictionIntegration", proxy_lambda)
        http_api.add_routes(path="/", methods=[aws_apigatewayv2.HttpMethod.POST], integration=prediction_integration)
        feedback_integration = aws_apigatewayv2_integrations.HttpLambdaIntegration("FeedbackIntegration", feedback_lambda)
        http_api.add_routes(path="/feedback", methods=[aws_apigatewayv2.HttpMethod.POST], integration=feedback_integration)

        # --- 2. The Final, Production-Ready Step Functions State Machine ---
        export_data_job = sfn_tasks.LambdaInvoke(self, "ExportVerifiedData",
            lambda_function=export_data_lambda, result_path="$.ExportResult")

        training_job = sfn_tasks.SageMakerCreateTrainingJob(self, "TrainNewModel",
            training_job_name=sfn.JsonPath.string_at("$$.Execution.Name"),
            algorithm_specification=sfn_tasks.AlgorithmSpecification(training_image=sfn_tasks.DockerImage.from_registry(image_uri)),
            input_data_config=[sfn_tasks.Channel(
                channel_name="train",
                data_source=sfn_tasks.DataSource(s3_data_source=sfn_tasks.S3DataSource(
                    s3_data_type=sfn_tasks.S3DataType.S3_PREFIX,
                    s3_location=sfn_tasks.S3Location.from_bucket(training_data_bucket, "training-data/"))))],
            output_data_config=sfn_tasks.OutputDataConfig(s3_output_location=sfn_tasks.S3Location.from_bucket(training_data_bucket, "training-output/")),
            role=sagemaker_role,
            resource_config=sfn_tasks.ResourceConfig(instance_count=1, instance_type=aws_ec2.InstanceType.of(aws_ec2.InstanceClass.M5, aws_ec2.InstanceSize.LARGE), volume_size=cdk.Size.gibibytes(10)),
            result_path="$.TrainingResult")
        
        create_model_job = sfn_tasks.SageMakerCreateModel(self, "CreateModel",
            model_name=sfn.JsonPath.string_at("$$.Execution.Name"),
            primary_container=sfn_tasks.ContainerDefinition(
                image=sfn_tasks.DockerImage.from_registry(image_uri)),
            role=sagemaker_role, result_path="$.CreateModelResult")

        create_endpoint_config_job = sfn_tasks.SageMakerCreateEndpointConfig(self, "CreateNewEndpointConfig",
            endpoint_config_name=sfn.JsonPath.string_at("$$.Execution.Name"),
            production_variants=[sfn_tasks.ProductionVariant(
                initial_instance_count=1,
                instance_type=aws_ec2.InstanceType.of(aws_ec2.InstanceClass.T2, cdk.aws_ec2.InstanceSize.MEDIUM),
                # FIX: Reference the model name from the execution context, not the result path
                model_name=sfn.JsonPath.string_at("$$.Execution.Name"),
                variant_name="AllTraffic")],
            result_path="$.CreateEndpointConfigResult")
        
        update_endpoint_job = sfn_tasks.SageMakerUpdateEndpoint(self, "UpdateLiveEndpoint",
            endpoint_name=sagemaker_endpoint.endpoint_name,
            endpoint_config_name=sfn.JsonPath.string_at("$$.Execution.Name"))

        # Define a success state for when there's no new data
        no_data_success_state = sfn.Succeed(self, "NoNewData")

        # Parse the JSON body from Lambda response
        parse_export_result = sfn.Pass(self, "ParseExportResult",
            parameters={
                "ExportResult.$": "$.ExportResult",
                "ParsedBody.$": "States.StringToJson($.ExportResult.Payload.body)"
            }
        )

        # Define the full workflow with the new Choice state
        definition = export_data_job.next(parse_export_result).next(
            sfn.Choice(self, "CheckForNewData")
            .when(
                # If the export lambda found records, proceed with training
                sfn.Condition.number_greater_than("$.ParsedBody.record_count", 0),
                training_job.next(create_model_job).next(create_endpoint_config_job).next(update_endpoint_job)
            )
            .otherwise(
                # If no new records, go to the success state
                no_data_success_state
            )
        )
        
        state_machine = sfn.StateMachine(self, "AutomatedRetrainingStateMachine",
            definition_body=sfn.DefinitionBody.from_chainable(definition),
            timeout=cdk.Duration.minutes(30))

        # --- 3. Outputs ---
        cdk.CfnOutput(self, "ApiEndpointUrl", value=http_api.url)
        cdk.CfnOutput(self, "PredictionsTableName", value=predictions_table.table_name)
        cdk.CfnOutput(self, "TrainingDataBucketName", value=training_data_bucket.bucket_name)
        cdk.CfnOutput(self, "RetrainingStateMachineArn", value=state_machine.state_machine_arn)
