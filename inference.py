import joblib
import pandas as pd
import numpy as np
from io import StringIO

def model_fn(model_dir):
    """Load the model from the model_dir"""
    model = joblib.load(f"{model_dir}/fraud_detection_model.joblib")
    return model

def input_fn(request_body, request_content_type):
    """Parse input data"""
    if request_content_type == 'text/csv':
        # Parse CSV input
        data = pd.read_csv(StringIO(request_body), header=None)
        return data.values
    else:
        raise ValueError(f"Unsupported content type: {request_content_type}")

def predict_fn(input_data, model):
    """Make predictions"""
    predictions = model.predict_proba(input_data)[:, 1]  # Get fraud probability
    return predictions

def output_fn(prediction, content_type):
    """Format the output"""
    if content_type == 'text/csv':
        return str(prediction[0])
    else:
        raise ValueError(f"Unsupported content type: {content_type}")