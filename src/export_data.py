import json
import boto3
import os
import csv
import io
from datetime import datetime
from decimal import Decimal

# --- Environment Variables ---
PREDICTIONS_TABLE_NAME = os.environ.get('PREDICTIONS_TABLE_NAME', '')
TRAINING_DATA_BUCKET_NAME = os.environ.get('TRAINING_DATA_BUCKET_NAME', '')

# --- AWS Clients ---
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')

class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert a DynamoDB item to JSON."""
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

def handler(event, context):
    """
    This function scans the DynamoDB table for verified feedback,
    formats the data into a CSV file, and uploads it to S3 for retraining.
    """
    print("Starting data export process...")

    if not PREDICTIONS_TABLE_NAME or not TRAINING_DATA_BUCKET_NAME:
        raise EnvironmentError("Required environment variables are not set.")

    table = dynamodb.Table(PREDICTIONS_TABLE_NAME)
    
    response = table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr('feedback_status').eq('VERIFIED')
    )
    
    verified_items = response.get('Items', [])
    print(f"Found {len(verified_items)} items with verified feedback.")

    if not verified_items:
        print("No new verified data to export. Exiting.")
        return {
            'statusCode': 200, 
            'body': json.dumps({
                'message': 'No new data to export.',
                'record_count': 0
            })
        }

    # --- Format the data for CSV ---
    # The first row of the CSV must be the target variable ('Class'),
    # followed by all the feature columns.
    header = ['Class'] + [f'V{i}' for i in range(1, 29)] + ['Amount']
    
    # in-memory text stream to build the CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(header)

    for item in verified_items:
        # The 'correct_label' is our new ground truth
        correct_label = item.get('correct_label')
        transaction_data = item.get('transaction_data', {})
        
        # Convert Decimal types back to float/int for processing
        transaction_data = json.loads(json.dumps(transaction_data, cls=DecimalEncoder))

        # Create the row in the correct order
        row = [correct_label] + [transaction_data.get(col, 0) for col in header[1:]]
        writer.writerow(row)

    # Get the CSV data as a string
    csv_content = output.getvalue()
    
    # --- Upload to S3 ---
    timestamp = datetime.utcnow().strftime('%Y-%m-%d-%H-%M-%S')
    s3_key = f"training-data/verified-data-{timestamp}.csv"
    
    try:
        s3_client.put_object(
            Bucket=TRAINING_DATA_BUCKET_NAME,
            Key=s3_key,
            Body=csv_content
        )
        print(f"Successfully uploaded new training data to s3://{TRAINING_DATA_BUCKET_NAME}/{s3_key}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Data export successful.',
                's3_bucket': TRAINING_DATA_BUCKET_NAME,
                's3_key': s3_key,
                'record_count': len(verified_items)
            })
        }
    except Exception as e:
        print(f"Error uploading to S3: {e}")
        raise e