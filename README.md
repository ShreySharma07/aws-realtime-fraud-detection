# # 🚀 Real-Time Fraud Detection Platform on AWS

<div align="center">

![AWS](https://img.shields.io/badge/AWS-%23FF9900.svg?style=for-the-badge&logo=amazon-aws&logoColor=white)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![Machine Learning](https://img.shields.io/badge/ML-XGBoost-green?style=for-the-badge)

**A complete serverless machine learning pipeline that detects fraudulent financial transactions in real-time**

*Built with professional-grade MLOps principles and Infrastructure as Code*

</div>

---

## 📊 Project Status

> **✅ Status: Completed & Fully Functional**

> **ℹ️ Note:** The live API endpoint and SageMaker instance have been decommissioned to adhere to AWS Free Tier limits and avoid incurring costs. This README provides the final working code, architecture details, and proof of successful deployment and inference.

---

## 🏗️ The Engineering Journey: From Simple Idea to Robust Architecture

This project was more than just building a pipeline; it was a **deep dive into the real-world challenges** of deploying large machine learning models in a serverless environment. The final architecture is the result of systematic debugging and pivoting based on platform limitations—a process common in professional engineering.

### 🎯 1. The Initial Goal: A Simple Serverless Function

The initial plan was to deploy the XGBoost model within a simple AWS Lambda function, triggered by an API Gateway. This is a common pattern for lightweight tasks.

> **⚠️ The Problem:** The deployment failed due to the **250 MB size limit** for Lambda function packages. The required libraries (scikit-learn, xgboost, numpy, pandas) were far too large.

### 🔄 2. The First Pivot: Lambda Layers

To solve the size limit, the architecture was changed to separate the large dependencies into a Lambda Layer.

> **⚠️ The Problem:** This introduced complex dependency issues. Manually creating the layer led to `ModuleNotFoundError` errors (`No module named 'joblib'`) because the packaging was incorrect for the Lambda Linux environment. Using the CDK's Docker-based build process (`PythonFunction`) solved the packaging issue but once again hit the **250 MB size limit**, this time for the Layer itself.

### 🎯 3. The Second Pivot: The Professional-Grade Solution

Hitting the hard size limit proved that Lambda was not the right tool for hosting large ML models. The project was re-architected to use the **industry-standard tool** for this exact job: **Amazon SageMaker**.

#### 🏗️ The New Architecture:

- **Amazon SageMaker:** Hosts the large XGBoost model on a dedicated, optimized inference endpoint
- **AWS Lambda:** Becomes a lightweight, lightning-fast "proxy" whose only job is to receive API requests and invoke the SageMaker endpoint
- **API Gateway:** Remains the public-facing REST API

### 🔐 4. The Final Challenge: Advanced IAM Permissions

Deploying the SageMaker architecture revealed the final, most advanced class of errors: **obscure IAM permissions issues**.

> **⚠️ The Problem:** The deployment failed with `ValidationException` errors like `does not grant ecr:GetDownloadUrlForLayer...` and `Could not access model data at s3://...`. Even with `AmazonSageMakerFullAccess`, the default role was not sufficient due to internal AWS race conditions and cross-service permission complexities.

> **✅ The Definitive Solution:** The final, working code solves this by adding **explicit IAM policy statements** to the SageMaker role, directly granting it the `s3:GetObject` and `ecr:Get*` permissions it needed. This robust, explicit approach is a **best practice** for complex cloud deployments.

---

## 🏛️ Final Architecture

The final architecture is **scalable**, **cost-effective**, and follows **AWS best practices** for deploying machine learning models.

```
[Client] ---> [API Gateway] ---> [Proxy Lambda] ---> [SageMaker Endpoint]
   |               (REST API)         (Simple Proxy)        (ML Model Hosting)
   |                                                           |
   |                                                           V
   '---------------------------------------------------- [S3 Model Artifact]
```

---

## 🛠️ Tech Stack

<div align="center">

| Category | Technologies |
|----------|-------------|
| ☁️ **Cloud Provider** | AWS |
| 🔧 **Core Services** | Amazon SageMaker, AWS Lambda, Amazon API Gateway, Amazon S3, IAM |
| 🏗️ **Infrastructure as Code** | AWS CDK (Python) |
| 🤖 **ML Model** | Python (XGBoost, Scikit-learn, Pandas, NumPy) |
| 🐳 **Containerization** | Docker (used by the CDK for packaging) |
| 📝 **Version Control** | Git & GitHub |

</div>

---

## ✅ Proof of Success

The final deployment was **successful**. The following curl command was used to send a sample transaction to the live API endpoint.

### 🧪 Test Request:

```bash
curl -X POST https://8jwpdmqgza.execute-api.ap-south-1.amazonaws.com/ \
  -H "Content-Type: application/json" \
  -d '{"V1":-1.36,"V2":-0.07,"V3":2.54,"V4":1.38,"V5":-0.34,"V6":0.46,"V7":0.24,"V8":0.10,"V9":0.36,"V10":0.09,"V11":-0.55,"V12":-0.62,"V13":-0.99,"V14":-0.31,"V15":1.47,"V16":-0.47,"V17":0.21,"V18":0.03,"V19":0.40,"V20":0.25,"V21":-0.02,"V22":0.28,"V23":-0.11,"V24":0.07,"V25":0.13,"V26":-0.19,"V27":0.13,"V28":-0.02,"Amount":149.62}'
```

### 🎉 Successful Response:

```json
{
  "is_fraud": false, 
  "fraud_score": 6.976925305934856e-06
}
```

> **✅ This response confirms that the end-to-end pipeline**—from the API Gateway, through the Lambda proxy, to the SageMaker endpoint, and back—was **fully functional**.

---

## 🚀 How to Run This Project

### 1️⃣ Clone the repository:

```bash
git clone https://github.com/ShreySharma07/aws-realtime-fraud-detection.git
cd aws-realtime-fraud-detection
```

### 2️⃣ Prerequisites:

- ✅ Ensure you have an AWS account and the AWS CLI configured (`aws configure`)
- ✅ Install Node.js v20 using nvm (`nvm install 20 && nvm use 20`)
- ✅ Install the AWS CDK globally (`npm install -g aws-cdk`)
- ✅ Install and run Docker Desktop

### 3️⃣ Train the Model:

```bash
# Run the model training script to generate the model.tar.gz artifact
python train_model.py
```

### 4️⃣ Deploy the Infrastructure:

```bash
# Navigate to the infra directory
cd infra

# Install Node.js dependencies
npm install

# Create and activate a Python virtual environment
python3 -m venv .venv && source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Deploy the stack to your AWS account
cdk deploy
```

### 5️⃣ Clean Up:

> **⚠️ IMPORTANT:** To avoid charges, destroy all created resources when you are finished.

```bash
cdk destroy
```

---

<div align="center">

### 🌟 **Built with ❤️ and professional MLOps practices**

*If you found this project helpful, please consider giving it a star!* ⭐

</div>
