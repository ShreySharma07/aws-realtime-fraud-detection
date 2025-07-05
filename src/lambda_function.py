import json
import joblib
import os
import boto3
import numpy as np


MODEL_BUCKET_NAME = os.environ.get('MODEL_BUCKET_NAME', '')
MODEL_FILE_KEY = os.environ.get('MODEL_FILE_KEY', 'fraud_detection_model.joblib')

s3_client = boto3.client('s3')

local_model_path = f'/tmp/{MODEL_FILE_KEY}'
s3_client.download_file(MODEL_BUCKET_NAME, MODEL_FILE_KEY, local_model_path)

model = joblib.load(local_model_path)

print('Model loaded successfully')

def handler(event, context):

    print('recieved event', json.dump(event))

    try:
        body = json.loads(event.get("body", '{}'))

        features_columns = ['Time'] + [f'V{i}' for i in range(1, 29)] + ['Amount']

        if not all(col in body for col in features_columns):
            return {
                'statusCode' : 400,
                'headers' : {'Content-Type': 'application/json'},
                'body' : json.dumps({'error': 'Missing one or more required features.'})
            }
        
        features = [body[col] for col in features_columns]

        transaction_array = np.array(features).reshape(1, -1)

        #Making a prediction
        prediction = model.predict(transaction_array)[0]
        prediction_proba = model.predict_proba(transaction_array)[0]

        response_body = {
            'is_fraud': bool(prediction),
            'fraud_probability': float(prediction_proba[1]),
            'model_version': MODEL_FILE_KEY
        }

        return {
            'statusCode': 200,
            'headers': {'Content-Type', 'application/json'},
            'body': json.dumps(response_body)
        }
    except Exception as e:
        print(f"Error processing request: {e}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Internal server error during prediction.'})
        }