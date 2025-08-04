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

[![Watch the demo](https://raw.githubusercontent.com/ShreySharma07/aws-realtime-fraud-detection/main/thumbnail.jpg)](https://youtu.be/C99CmyPCk3U)

---

🏛️ Architecture
The platform is architected using a modern, serverless-first approach on AWS, separating the low-latency real-time inference path from the asynchronous, event-driven retraining path.
<!-- Add your architecture diagram here -->
<p align="center">
<img src=".github/assets/architecture.png" alt="Aura Platform Architecture Diagram">
</p>
✨ Core Features & Screenshots
Aura is a multi-layered platform designed to solve real-world business problems.
FeatureDescription & ScreenshotReal-Time API & Analyst DashboardAn interactive Streamlit dashboard serves as the command center for fraud analysts. It connects to a live API Gateway endpoint that triggers a lightweight AWS Lambda proxy. This proxy invokes a high-performance Amazon SageMaker endpoint hosting an XGBoost model, returning predictions with <200ms p99 latency and a 97.7% AUC score.<br><br><!-- Add dashboard screenshot here --><img src=".github/assets/dashboard.png" alt="Analyst Dashboard Screenshot">GenAI Fraud Investigator (XAI)To provide Explainable AI, the Lambda proxy enriches high-risk predictions by calling the Gemini API. It generates a human-readable summary explaining why a transaction was flagged, based on its most anomalous features. This drastically reduces manual investigation time.<br><br><!-- Add XAI screenshot here --><img src=".github/assets/genai_investigator.png" alt="GenAI Investigator Screenshot">Hybrid Rule EngineA pre-screening layer of simple business rules catches extreme outliers (e.g., transaction amounts > $25,000) before they are sent to the ML model. This increases system robustness and prevents unreliable predictions on out-of-distribution data.Human-in-the-Loop (HITL) SystemThe dashboard allows analysts to submit feedback ("Correct" / "Incorrect") on model predictions. This feedback is sent to a dedicated /feedback API endpoint, triggering a second Lambda function that updates the prediction record in a DynamoDB table, changing its status from PENDING to VERIFIED.<br><br><!-- Add HITL screenshot here --><img src=".github/assets/hitl_feedback.png" alt="HITL Feedback System Screenshot">Automated Retraining PipelineA complete MLOps pipeline orchestrated by AWS Step Functions. On a schedule, it automatically exports the human-verified data from DynamoDB to S3, starts a new SageMaker Training Job, creates a new model, and performs a zero-downtime "blue/green" deployment by updating the live SageMaker endpoint with the new, smarter model.<br><br><!-- Add Step Functions screenshot here --><img src=".github/assets/step_functions.png" alt="Step Functions Pipeline Screenshot">Statistical IntelligenceA dedicated dashboard section provides deep data science insights, including a SHAP analysis chart to explain global feature importance and a business impact analysis that quantifies the correlation between key features and financial risk.<br><br><!-- Add SHAP analysis screenshot here --><img src=".github/assets/shap_analysis.png" alt="SHAP Analysis Screenshot">
🏗️ The Engineering Journey: From Simple Idea to Robust Architecture
This project was more than just building a pipeline; it was a deep dive into the real-world challenges of deploying large machine learning models in a serverless environment. The final architecture is the result of systematic debugging and pivoting based on platform limitations—a process common in professional engineering.
🎯 1. The Initial Goal: A Simple Serverless Function
The initial plan was to deploy the XGBoost model within a simple AWS Lambda function, triggered by an API Gateway. This is a common pattern for lightweight tasks.
⚠️ The Problem: The deployment failed due to the 250 MB size limit for Lambda function packages. The required libraries (scikit-learn, xgboost, numpy, pandas) were far too large.
🔄 2. The First Pivot: Lambda Layers
To solve the size limit, the architecture was changed to separate the large dependencies into a Lambda Layer.
⚠️ The Problem: This introduced complex dependency issues. Manually creating the layer led to ModuleNotFoundError errors (No module named 'joblib') because the packaging was incorrect for the Lambda Linux environment. Using the CDK's Docker-based build process (PythonFunction) solved the packaging issue but once again hit the 250 MB size limit, this time for the Layer itself.
🎯 3. The Second Pivot: The Professional-Grade Solution
Hitting the hard size limit proved that Lambda was not the right tool for hosting large ML models. The project was re-architected to use the industry-standard tool for this exact job: Amazon SageMaker.
🏗️ The New Architecture:

Amazon SageMaker: Hosts the large XGBoost model on a dedicated, optimized inference endpoint
AWS Lambda: Becomes a lightweight, lightning-fast "proxy" whose only job is to receive API requests and invoke the SageMaker endpoint
API Gateway: Remains the public-facing REST API

🔐 4. The Final Challenge: Advanced IAM Permissions
Deploying the SageMaker architecture revealed the final, most advanced class of errors: obscure IAM permissions issues.
⚠️ The Problem: The deployment failed with ValidationException errors like "does not grant ecr:GetDownloadUrlForLayer..." and "Could not access model data at s3://....". Even with AmazonSageMakerFullAccess, the default role was not sufficient due to internal AWS race conditions and cross-service permission complexities.
✅ The Definitive Solution: The final, working code solves this by adding explicit IAM policy statements to the SageMaker role, directly granting it the s3:GetObject and ecr:Get* permissions it needed. This robust, explicit approach is a best practice for complex cloud deployments.
💡 Additional Challenges & Solutions
Challenge: The automated retraining pipeline initially failed with a ValidationException when trying to update the live endpoint.
Solution: Diagnosed this as a "blue/green" deployment issue. The Step Functions workflow was upgraded to create a new endpoint configuration for the new model before updating the live endpoint, a professional-grade MLOps pattern.
Challenge: The project involved numerous advanced IAM permissions issues between services.
Solution: Solved these by adding explicit, granular IAM policies to the service roles, moving beyond default managed policies to ensure robust and secure cross-service communication.
🛠️ Tech Stack
CategoryTechnologies☁️ Cloud ProviderAWS🔧 Core ServicesAmazon SageMaker, AWS Lambda, AWS Step Functions, Amazon API Gateway, Amazon S3, Amazon DynamoDB, IAM🏗️ Infrastructure as CodeAWS CDK (Python)🤖 ML ModelPython (XGBoost, Scikit-learn, Pandas, NumPy)📊 Data Science & AnalyticsStreamlit, Plotly, SHAP🤖 Generative AIGoogle Gemini API🐳 ContainerizationDocker (used by the CDK for packaging)📝 Version ControlGit & GitHub
✅ Proof of Success
The final deployment was successful. The following curl command was used to send a sample transaction to the live API endpoint.
🧪 Test Request:
bashcurl -X POST https://8jwpdmqgza.execute-api.ap-south-1.amazonaws.com/ \
  -H "Content-Type: application/json" \
  -d '{"V1":-1.36,"V2":-0.07,"V3":2.54,"V4":1.38,"V5":-0.34,"V6":0.46,"V7":0.24,"V8":0.10,"V9":0.36,"V10":0.09,"V11":-0.55,"V12":-0.62,"V13":-0.99,"V14":-0.31,"V15":1.47,"V16":-0.47,"V17":0.21,"V18":0.03,"V19":0.40,"V20":0.25,"V21":-0.02,"V22":0.28,"V23":-0.11,"V24":0.07,"V25":0.13,"V26":-0.19,"V27":0.13,"V28":-0.02,"Amount":149.62}'
🎉 Successful Response:
json{
  "is_fraud": false, 
  "fraud_score": 6.976925305934856e-06
}
✅ This response confirms that the end-to-end pipeline—from the API Gateway, through the Lambda proxy, to the SageMaker endpoint, and back—was fully functional.
🚀 How to Run This Project
1️⃣ Clone the repository:
bashgit clone https://github.com/ShreySharma07/aws-realtime-fraud-detection.git
cd aws-realtime-fraud-detection
2️⃣ Prerequisites:
✅ Ensure you have an AWS account and the AWS CLI configured (aws configure)
✅ Install Node.js v20 using nvm (nvm install 20 && nvm use 20)
✅ Install the AWS CDK globally (npm install -g aws-cdk)
✅ Install and run Docker Desktop
3️⃣ Train the Model:
bash# Run the model training script to generate the model.tar.gz artifact
python train_model.py
4️⃣ Deploy the Infrastructure:
bash# Navigate to the infra directory
cd infra

# Install Node.js dependencies
npm install

# Create and activate a Python virtual environment
python3 -m venv .venv && source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Deploy the stack to your AWS account, passing your Gemini API key as a context variable
cdk deploy --context gemini_api_key="YOUR_API_KEY_HERE"
5️⃣ Run the Dashboard:
bash# Navigate back to the root project folder
cd ..

# Activate the main virtual environment
source venv/bin/activate

# Run the Streamlit app
streamlit run dashboard_app.py
6️⃣ Clean Up:
⚠️ IMPORTANT: To avoid charges, destroy all created resources when you are finished.
bashcd infra
cdk destroy