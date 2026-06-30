import streamlit as st
from google import genai
from google.genai import types
import json
import pandas as pd
from datetime import datetime
import os

# ==========================================
# SYSTEM CONFIGURATION
# ==========================================
api_key = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=api_key)

st.set_page_config(page_title="APSS - Advanced Audit", layout="wide")

# ==========================================
# LOGGING SYSTEM
# ==========================================
def save_log(res, doc_files, prod_files):
    log_entry = {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Score": res['consistency_score'],
        "Summary": res['summary'],
        "Docs": ", ".join([f.name for f in doc_files]),
        "Issues": "; ".join(res.get('key_issues', []))
    }
    df = pd.DataFrame([log_entry])
    file_path = "audit_log.csv"
    if not os.path.exists(file_path):
        df.to_csv(file_path, index=False)
    else:
        df.to_csv(file_path, mode='a', header=False, index=False)

# ==========================================
# AI ENGINE: 8-STEP STRICTOR AUDIT
# ==========================================
def perform_audit(doc_files, prod_files):
    prompt = """
    Perform an expert industrial logistics audit. 
    STRICT RULES:
    1. Focus ONLY on 'Item Identity' and 'Quantity'. 
    2. ABSOLUTELY IGNORE all data related to Weight, Dimensions, Shipping Dates, or Consignee.
    3. Return JSON strictly in this format:
    {
        "summary": "Professional summary of the audit.",
        "doc_description": "Declared items and quantities.",
        "physical_description": "Observed items and quantities.",
        "comparison": [
            {"Aspect": "Item Identity", "Doc": "...", "Physical": "..."}, 
            {"Aspect": "Quantity", "Doc": "...", "Physical": "..."}
        ],
        "audit_checklist": {
            "Part_Number": "score/15", "Authenticity": "score/15", "Visual_Fidelity": "score/20",
            "Outer_Count": "score/20", "Inner_Count": "score/20", 
            "Label_Integrity": "score/5", "Unmanifested_Items": "score/3", "Label_Clarity": "score/2"
        },
        "consistency_score": 0,
        "key_issues": ["Issue list"]
    }
    """
    contents = [prompt]
    for f in doc_files:
        contents.append(types.Part.from_bytes(data=f.read(), mime_type=f.type))
    for f in prod_files:
        contents.append(types.Part.from_bytes(data=f.read(), mime_type=f.type))

    response = client.models.generate_content(
        model='models/gemini-2.5-flash',
        contents=contents,
        config=types.GenerateContentConfig(temperature=0.0)
    )
    return json.loads(response.text.replace('```json', '').replace('```', '').strip())

# ==========================================
# WEB UI: DASHBOARD
# ==========================================
tab1, tab2 = st.tabs(["🚀 New Audit", "📜 Audit History"])

with tab1:
    st.title("📦 APSS - Advanced Logistics Audit")
    c1, c2 = st.columns(2)
    with c1:
        doc_files = st.file_uploader("Upload Documents", type=["pdf", "jpg", "png"], accept_multiple_files=True)
    with c2:
        prod_files = st.file_uploader("Upload Product Images", type=["jpg", "png"], accept_multiple_files=True)

    if st.button("🚀 EXECUTE FULL AUDIT", type="primary"):
        if doc_files and prod_files:
            with st.spinner('AI auditing in progress...'):
                try:
                    res = perform_audit(doc_files, prod_files)
                    save_log(res, doc_files, prod_files)
                    
                    st.markdown(f"## Consistency Score: {res['consistency_score']}%")
                    st.progress(res['consistency_score'] / 100)
                    st.info(res['summary'])

                    colA, colB = st.columns(2)
                    with colA:
                        st.markdown("**📄 Document Extraction**")
                        st.write(res.get('doc_description', 'N/A'))
                    with colB:
                        st.markdown("**📦 Physical Observation**")
                        st.write(res.get('physical_description', 'N/A'))

                    st.markdown("### 📊 Verification Details")
                    st.table(res['comparison'])

                    st.markdown("### ✅ Detailed Audit Checklist")
                    checklist = res.get('audit_checklist', {})
                    st.table([{"Step": k.replace('_', ' '), "Score": v} for k, v in checklist.items()])

                    st.markdown("### 🔍 Key Issues")
                    for issue in res.get('key_issues', []):
                        st.warning(f"⚠️ {issue}")
                except Exception as e:
                    st.error(f"Audit Error: {e}")
        else:
            st.warning("Please upload both documents and images.")

with tab2:
    st.markdown("### 📜 Audit History")
    if os.path.exists("audit_log.csv"):
        log_df = pd.read_csv("audit_log.csv")
        st.dataframe(log_df.sort_values(by="Timestamp", ascending=False))
        st.download_button("📥 Download Log (CSV)", data=log_df.to_csv(index=False), file_name="audit_report.csv")
    else:
        st.info("No audit logs found yet.")
