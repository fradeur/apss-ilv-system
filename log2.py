import streamlit as st
from google import genai
from google.genai import types
import json

# ==========================================
# SYSTEM CONFIGURATION
# ==========================================
api_key = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=api_key)

st.set_page_config(page_title="APSS - Advanced Audit", layout="wide")

# ==========================================
# AI ENGINE: 8-STEP STRICTOR AUDIT
# ==========================================
def perform_audit(doc_files, prod_files):
    prompt = """
    Perform an expert industrial logistics audit using an 8-step verification process.
    
    1. Item Identity & Integrity (50 pts):
       - Part Number Check (15 pts): Verify exact part code matches.
       - Authenticity/Quality (15 pts): Check if item appears New/Original.
       - Visual Fidelity (20 pts): Match shape, finish, and specs.
       - KNOCK-OUT: Incorrect Part Number = 0% total score immediately.

    2. Quantity Verification (40 pts):
       - Outer Manifest/Pallet Count (20 pts): Verify shipping containers.
       - Inner Unit Count (20 pts): Verify actual items per box.
       - PENALTY: Apply heavy exponential penalty for any deviation in either category.

    3. Extras & Labeling (10 pts):
       - Label Integrity (5 pts): Check for cross-labeling or misleading tags.
       - Unmanifested Items (3 pts): Detect extra/foreign parts.
       - Label Clarity (2 pts): Ensure readability.

    Calculate points for each sub-category above.
    
    Return JSON strictly in this format:
    {
        "summary": "Professional summary of the shipment audit.",
        "doc_description": "Declared details in documents.",
        "physical_description": "Observed details in images.",
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
# WEB UI: DASHBOARD STYLE
# ==========================================
st.title("📦 APSS - Logistics Audit Dashboard (v3.0)")
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    doc_files = st.file_uploader("Upload Documents", type=["pdf", "jpg", "png"], accept_multiple_files=True)
with col2:
    prod_files = st.file_uploader("Upload Product Images", type=["jpg", "png"], accept_multiple_files=True)

if st.button("🚀 EXECUTE 8-STEP ADVANCED AUDIT", type="primary"):
    if doc_files and prod_files:
        with st.spinner('AI conducting 8-step inspection...'):
            try:
                res = perform_audit(doc_files, prod_files)

                # SCORE
                st.markdown(f"## Consistency Score: {res['consistency_score']}%")
                st.progress(res['consistency_score'] / 100)

                # 8-STEP CHECKLIST TABLE
                st.markdown("### ✅ Detailed Audit Checklist")
                checklist = res.get('audit_checklist', {})
                data = [{"Step": k.replace('_', ' '), "Score": v} for k, v in checklist.items()]
                st.table(data)

                # CONTEXT & ISSUES
                st.markdown("### 📝 Analysis Details")
                st.info(res['summary'])
                
                st.markdown("### 🔍 Issues")
                for issue in res.get('key_issues', []):
                    st.warning(f"⚠️ {issue}")

                if res['consistency_score'] < 100:
                    if st.button("Override and Force PASS"):
                        st.success("✅ Audit result manually overridden.")
            except Exception as e:
                st.error(f"Error: {e}")
