import streamlit as st
import pandas as pd
import plotly.express as px
import os
import requests
import json
import joblib
import shap

# --- Page Configuration ---
st.set_page_config(
    page_title="Aura: Trust & Safety Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_ENDPOINT = "https://bnm4ojywee.execute-api.ap-south-1.amazonaws.com/" 
FEEDBACK_ENDPOINT = f"{API_ENDPOINT}feedback"

# --- Asset Loading ---
@st.cache_data
def load_data():
    """Loads the credit card fraud dataset."""
    try:
        data_path = os.path.join('data', 'creditcard.csv')
        df = pd.read_csv(data_path)
        stats = {
            'V4_upper': df['V4'].quantile(0.999),
            'V14_lower': df['V14'].quantile(0.001),
            'Amount_upper': 25000
        }
        return df, stats
    except FileNotFoundError:
        st.error(f"Error: The data file was not found at '{data_path}'.")
        return None, None

@st.cache_resource
def load_model_and_explainer():
    """Loads the local XGBoost model and creates a SHAP explainer."""
    try:
        model_path = os.path.join('model_artifacts', 'fraud_detection_model.joblib')
        model = joblib.load(model_path)
        explainer = shap.TreeExplainer(model)
        return model, explainer
    except FileNotFoundError:
        st.warning(f"Local model not found at '{model_path}'. Feature importance analysis will be disabled.")
        return None, None

df, data_stats = load_data()
model, explainer = load_model_and_explainer()

# --- Helper Functions ---
def run_rule_engine(transaction_data, stats):
    amount = transaction_data.get('Amount', 0)
    v4 = transaction_data.get('V4', 0)
    v14 = transaction_data.get('V14', 0)
    if amount > stats['Amount_upper']: return f"Transaction amount of ${amount:,.2f} exceeds the business limit."
    if v4 > stats['V4_upper']: return f"Feature V4 value of {v4:.2f} is an extreme outlier."
    if v14 < stats['V14_lower']: return f"Feature V14 value of {v14:.2f} is an extreme outlier."
    return None

def get_ml_prediction(transaction_data):
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(API_ENDPOINT, data=json.dumps(transaction_data), headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: Could not connect to the endpoint. Details: {e}")
        return None

def submit_feedback(prediction_id, correct_label):
    """Calls the new /feedback endpoint to submit a correction."""
    try:
        payload = {"prediction_id": prediction_id, "correct_label": correct_label}
        headers = {'Content-Type': 'application/json'}
        response = requests.post(FEEDBACK_ENDPOINT, data=json.dumps(payload), headers=headers)
        response.raise_for_status()
        st.toast(f"Feedback submitted successfully for {prediction_id}!", icon="🎉")
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: Could not submit feedback. Details: {e}")
        return None

# --- Main Application ---
if df is not None:
    st.sidebar.title("Fraud Command Center")
    page = st.sidebar.radio("Navigate", ["Live Investigation", "Statistical Intelligence"])
    
    st.title("Trust & Safety Platform")

    if page == "Live Investigation":
        st.header("GenAI Fraud Investigator")
        col_input, col_results = st.columns([1, 1.5])

        with col_input:
            st.subheader("Investigation Method")
            tab1, tab2 = st.tabs(["Manual Input", "Select from Table"])

            def process_investigation(payload):
                with st.spinner("Analyzing transaction..."):
                    rule_broken_reason = run_rule_engine(payload, data_stats)
                    if rule_broken_reason:
                        st.session_state.prediction_result = {'source': 'Rule-Based Engine', 'is_fraud': True, 'fraud_score': 1.0, 'explanation': rule_broken_reason, 'prediction_id': 'N/A-RuleBased'}
                    else:
                        ml_result = get_ml_prediction(payload)
                        if ml_result:
                            ml_result['source'] = 'Machine Learning Model'
                            st.session_state.prediction_result = ml_result
            
            with tab1:
                st.markdown("Enter transaction details manually or load an example.")
                fraud_example = df[df['Class'] == 1].iloc[5]
                if st.button("Load Fraudulent Example"):
                    st.session_state.v1_input = fraud_example['V1']
                    st.session_state.v4_input = fraud_example['V4']
                    st.session_state.v14_input = fraud_example['V14']
                    st.session_state.amount_input = fraud_example['Amount']

                with st.form("manual_transaction_form"):
                    v1_input = st.number_input("Feature V1", value=st.session_state.get('v1_input', -2.30), format="%.2f")
                    v4_input = st.number_input("Feature V4", value=st.session_state.get('v4_input', 1.38), format="%.2f")
                    v14_input = st.number_input("Feature V14", value=st.session_state.get('v14_input', -2.80), format="%.2f")
                    amount_input = st.number_input("Transaction Amount ($)", value=st.session_state.get('amount_input', 149.62), format="%.2f")
                    
                    submitted = st.form_submit_button("Investigate Manual Transaction")
                    if submitted:
                        base_row = df[df['Class'] == 0].iloc[0].to_dict()
                        payload = base_row
                        payload.update({'V1': v1_input, 'V4': v4_input, 'V14': v14_input, 'Amount': amount_input})
                        process_investigation(payload)
                        for key in ['v1_input', 'v4_input', 'v14_input', 'amount_input']:
                            if key in st.session_state: del st.session_state[key]
            
            with tab2:
                st.markdown("Select a transaction from the table below.")
                sample_df = pd.concat([df[df['Class'] == 0].head(50), df[df['Class'] == 1].head(50)]).reset_index()
                if 'selected_index' not in st.session_state: st.session_state.selected_index = None
                
                selected_indices = st.multiselect('Select a transaction:', options=sample_df.index, max_selections=1,
                    format_func=lambda x: f"Txn #{sample_df.loc[x, 'index']} - Amount: ${sample_df.loc[x, 'Amount']:.2f} ({'Fraud' if sample_df.loc[x, 'Class']==1 else 'Safe'})")
                
                if selected_indices: st.session_state.selected_index = selected_indices[0]
                
                if st.button("Investigate Selected Transaction"):
                    if st.session_state.selected_index is not None:
                        process_investigation(sample_df.loc[st.session_state.selected_index].to_dict())
                    else:
                        st.warning("Please select a transaction first.")

        with col_results:
            st.subheader("Investigation Results")
            if 'prediction_result' in st.session_state and st.session_state.prediction_result:
                result = st.session_state.prediction_result
                
                st.markdown(f"**Detection Source:** `{result.get('source', 'N/A')}`")
                st.markdown(f"**Prediction ID:** `{result.get('prediction_id', 'N/A')}`")

                if result.get('is_fraud'):
                    st.error("**Fraud Alert!**")
                else:
                    st.success("**Transaction Appears Safe**")
                
                st.metric(label="Model Fraud Score", value=f"{result.get('fraud_score', 0):.4f}")
                
                st.markdown("---")
                st.subheader("AI Analyst Explanation:")
                st.info(result.get('explanation', "No explanation provided."))

                # --- NEW: Feedback Buttons ---
                st.markdown("---")
                st.subheader("Submit Feedback (Human-in-the-Loop)")
                st.write("Was the model's prediction correct? Your feedback will be used to retrain and improve the model over time.")
                
                feedback_col1, feedback_col2 = st.columns(2)
                with feedback_col1:
                    if st.button("Confirm as SAFE (Not Fraud)", key="safe_feedback"):
                        if result.get('prediction_id') != 'N/A-RuleBased':
                            submit_feedback(result['prediction_id'], 0)
                        else:
                            st.warning("Cannot submit feedback for rule-based detections.")
                with feedback_col2:
                    if st.button("Confirm as FRAUD", key="fraud_feedback"):
                        if result.get('prediction_id') != 'N/A-RuleBased':
                            submit_feedback(result['prediction_id'], 1)
                        else:
                            st.warning("Cannot submit feedback for rule-based detections.")
            else:
                st.info("Results will appear here after an investigation is run.")

    elif page == "Statistical Intelligence":
        st.header("Statistical Intelligence Layer")
        st.markdown("This section provides deep, statistically rigorous insights into model behavior and business impact.")

        if model is not None and explainer is not None:
            st.subheader("Global Feature Importance (SHAP Analysis)")
            st.markdown("This chart shows the features that have the biggest impact on the model's predictions, averaged across all transactions.")
            
            sample_for_shap = df.drop('Class', axis=1).sample(1000, random_state=42)
            shap_values = explainer(sample_for_shap)

            fig = go.Figure()
            mean_abs_shap = pd.DataFrame(shap_values.values, columns=sample_for_shap.columns).abs().mean().sort_values(ascending=False)
            
            fig.add_trace(go.Bar(y=mean_abs_shap.index[:10], x=mean_abs_shap.values[:10], orientation='h'))
            fig.update_layout(title="Top 10 Most Impactful Features", xaxis_title="Mean Absolute SHAP Value", yaxis_title="Feature", yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Quantifying Business Impact")
            st.markdown("This analysis shows how different values of **V14** (a top predictor) correlate with the fraud rate and financial risk.")
            
            df['V14_bin'] = pd.qcut(df['V14'], q=10, duplicates='drop')
            impact_analysis = df.groupby('V14_bin').agg(
                fraud_rate=('Class', 'mean'),
                average_amount_at_risk=('Amount', lambda x: df.loc[x.index][df.loc[x.index]['Class']==1]['Amount'].mean())
            ).reset_index()
            impact_analysis['V14_bin'] = impact_analysis['V14_bin'].astype(str)

            fig_impact = px.bar(impact_analysis, x='V14_bin', y='fraud_rate', hover_data=['average_amount_at_risk'],
                labels={'V14_bin': 'V14 Value Range (Deciles)', 'fraud_rate': 'Fraud Rate'}, title="Fraud Rate by V14 Value Range")
            st.plotly_chart(fig_impact, use_container_width=True)
            st.info("Transactions with highly negative values for V14 have a significantly higher fraud rate, confirming it as a critical indicator of risk.")
        else:
            st.error("Could not load the local model. Statistical analysis is disabled.")
