import json
import boto3
import os
import urllib3
import uuid
from datetime import datetime

SAGEMAKER_ENDPOINT_NAME = os.environ.get('SAGEMAKER_ENDPOINT_NAME', '')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY',"")
PREDICTIONS_TABLE_NAME = os.environ.get('PREDICTIONS_TABLE_NAME', '')

sagemaker_runtime = boto3.client('sagemaker-runtime')
dynamodb = boto3.resource('dynamodb')
http = urllib3.PoolManager()


def get_gemini_explaination(transaction_data, fraud_score):
    
    if not GEMINI_API_KEY:
        return 'Gemini api key not configured, cannot generate explainations'
    
    prompt_features = {
        'Amount': transaction_data.get('Amount'),
        "V4": transaction_data.get("V4"),
        "V10": transaction_data.get("V10"),
        "V12": transaction_data.get("V12"),
        "V14": transaction_data.get("V14")
    }

    prompt = f"""
    You are an expert fraud analyst. A transaction was flagged with a high fraud score of {fraud_score:.2f}.
    Based on the following key data points, provide a brief, 2-3 bullet point explanation for why this transaction is suspicious.
    Do not use technical jargon. Explain it in simple terms for a business user.

    Key Transaction Data:
    {json.dumps(prompt_features, indent=2)}
    """

    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents":[{
            "parts":[{
                "text":prompt
            }]
        }]
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = http.request(
            "POST",
            gemini_url,
            body = json.dumps(payload),
            headers = headers,
            retries = False
        )

        response_data = json.loads(response.data.decode('utf-8'))

        explaination = response_data['candidates'][0]['content']['parts'][0]['text']

        return explaination.strip()
    
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return "Could not generate an explanation due to an API error."



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

        fraud_score = float(prediction)
        is_fraud = float(prediction) > 0.5
        explanation = 'N/A'

        #encriching response with explainations
        if is_fraud:
            explanation = get_gemini_explaination(transaction_data, fraud_score)

        # Store prediction in DynamoDB
        prediction_id = str(uuid.uuid4())
        if PREDICTIONS_TABLE_NAME:
            try:
                table = dynamodb.Table(PREDICTIONS_TABLE_NAME)
                table.put_item(
                    Item={
                        'predictionID': prediction_id,
                        'timestamp': datetime.utcnow().isoformat(),
                        'is_fraud': is_fraud,
                        'fraud_score': fraud_score,
                        'explanation': explanation,
                        'transaction_amount': transaction_data.get('Amount', 0)
                    }
                )
            except Exception as e:
                print(f"Error storing prediction in DynamoDB: {e}")

        #----format the successful response----
        return {
            'statusCode': 200,
            'headers': { 'Content-Type': 'application/json',
                        "Access-Control-Allow-Origin": "*"},
            'body': json.dumps({
                'prediction_id': prediction_id,
                'is_fraud': is_fraud,
                'fraud_score': fraud_score,
                'explanation': explanation
            })
        }
    
    except Exception as e:
        print(f'Error processing request: {e}')
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json',
                        "Access-Control-Allow-Origin": "*" },
            'body': json.dumps({'error': 'Internal server error.'})
        }