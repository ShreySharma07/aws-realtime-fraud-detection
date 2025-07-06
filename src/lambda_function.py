import json
import boto3
import os

SAGEMAKER_ENDPOINT_NAME = os.environ.get('SAGEMAKER_ENDPOINT_NAME', '')

sagemaker_runtime = boto3.client('sagemaker-runtime')

def handler(event, context):

    print('Recieved event', json.dumps(event))

    try:

        body = event.get('body', '{}')

        transaction_data = json.loads(body)

        feature_columns = [f'V{i}' for i in range(1, 29)] + ['Amount']

        payload_values = [transaction_data[col] for col in feature_columns]

        csv_payload = ','.join(map(str, payload_values))

        response = sagemaker_runtime.invoke_endpoint(
            EndpointName = SAGEMAKER_ENDPOINT_NAME,
            ContentType = 'text/csv',
            Body = csv_payload
        )

        prediction = response['Body'].read().decode('utf-8')

        #----format the successful response----
        return {
            'statusCode': 200,
            'headers': { 'Content-Type': 'application/json'},
            'body': json.dumps({
                'is_fraud': bool(float(prediction) > 0.5),
                'fraud_score': float(prediction)
            })
        }
    
    except Exception as e:
        print(f'Error processing request: {e}')
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json' },
            'body': json.dumps({'error': 'Internal server error.'})
        }