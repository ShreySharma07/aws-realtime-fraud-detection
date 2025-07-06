import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
import pickle
import os

# Load data
df = pd.read_csv('data/creditcard.csv')

# Prepare features
feature_columns = [f'V{i}' for i in range(1, 29)] + ['Amount']
X = df[feature_columns]
y = df['Class']

# Split data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train XGBoost model
model = xgb.XGBClassifier(random_state=42)
model.fit(X_train, y_train)

# Save model in XGBoost format
os.makedirs('xgb_model', exist_ok=True)
model.save_model('xgb_model/xgboost-model')

print("XGBoost model created successfully")