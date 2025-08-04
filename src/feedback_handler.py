import json
import boto3
import os
from datetime import datetime

PREDICTIONS_TABLE_NAME = os.environ.get('PREDICTIONS_TABLE_NAME','')

dynamo_db = boto3.resource('dynamodb')

def handler(event, context):

    print("Received feedback event", json.dumps(event))

    try:
        body = json.loads(event.get('body', '{}'))
        prediction_id = body.get('prediction_id')
        correct_label = body.get('correct_label')

        if not prediction_id or correct_label is None:
            raise ValueError("Missing 'prediction_id' or 'correct_label' in the request body.")
        
        if PREDICTIONS_TABLE_NAME:
            table = dynamo_db.Table(PREDICTIONS_TABLE_NAME)
            print(f"Updating item {prediction_id} with correct_label {correct_label}...")

            response = table.update_item(
                Key={'predictionId': prediction_id},
                UpdateExpression="SET correct_label = :label, feedback_status = :status, feedback_timestamp = :ts",
                ExpressionAttributeValues={
                    ':label': int(correct_label), # Ensure it's an integer (0 or 1)
                    ':status': 'VERIFIED',
                    ':ts': datetime.utcnow().isoformat()
                },
                ReturnValues="UPDATED_NEW" # Returns the new values of the updated attributes
            )
            
            print("Successfully updated item in DynamoDB. Response:", response)
            
            return {
                'statusCode': 200,
                'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
                'body': json.dumps({'message': f'Successfully recorded feedback for prediction {prediction_id}'})
            }
        else:
            raise EnvironmentError("PREDICTIONS_TABLE_NAME environment variable is not set.")

    except Exception as e:
        print(f"Error processing feedback: {e}")
        return {
            'statusCode': 500,
            'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({'error': 'Internal server error while processing feedback.'})
        }
