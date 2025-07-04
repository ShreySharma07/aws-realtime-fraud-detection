import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from imblearn.over_sampling import SMOTE
import joblib # To save the model

try:
    df = pd.read_csv('data/creditcard.csv')
    print("Dataset loaded successfully.")
    print("Dataset shape:", df.shape)
except FileNotFoundError:
    print("Error: 'creditcard.csv' not found. Please make sure it's in the same folder as this script.")
    exit()

X = df.drop('Class', axis=1)
y = df['Class']

print("\nClass distribution before SMOTE:")
print(y.value_counts())

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

print("\nApplying SMOTE to the training data... (This may take a moment)")
smote = SMOTE(random_state=42)
X_train_smote, y_train_smote = smote.fit_resample(X_train, y_train)

print("\nClass distribution after SMOTE:")
print(y_train_smote.value_counts())

print("\nTraining the XGBoost model...")

model = xgb.XGBClassifier(
    objective='binary:logistic',
    eval_metric='auc',
    use_label_encoder=False, 
    random_state=42
)

model.fit(X_train_smote, y_train_smote)
print("Model training complete.")

print("\nEvaluating the model on the test set...")
y_pred_test = model.predict(X_test)
y_pred_proba_test = model.predict_proba(X_test)[:, 1]

print("\n--- Evaluation Results ---")
print("\nClassification Report:")
print(classification_report(y_test, y_pred_test))

print("\nConfusion Matrix:")
print(confusion_matrix(y_test, y_pred_test))

print("\nArea Under ROC Curve (AUC-ROC):")
print(roc_auc_score(y_test, y_pred_proba_test))
print("--------------------------")

model_filename = 'fraud_detection_model.joblib'
joblib.dump(model, model_filename)
print(f"\nModel saved successfully as '{model_filename}'")
