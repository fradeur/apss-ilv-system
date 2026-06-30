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
    Perform an expert industrial logistics audit. 
    Return JSON strictly in this format:
    {
        "summary": "One sentence overall summary of the audit result.",
        "doc_description": "Summary of declared items and quantities in documents.",
        "physical_description": "Summary of observed items and quantities in images.",
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
    
    SCORING LOGIC:
    - Item Identity (50 pts): Split into Part Number (15), Authenticity (15), Visual Fidelity (20). KNOCK-OUT: Wrong Part Number = 0% total.
    - Quantity (40 pts): Outer Count (20), Inner Count (20). Exponential penalty for deviations.
    - Labeling (10 pts): Integrity (5), Unmanifested (3), Clarity (2).
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
st.title("📦 APSS - Advanced Logistics Audit Dashboard")
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    doc_files = st.file_uploader("Upload Documents (PDF/Img)", type=["pdf", "jpg", "png"], accept_multiple_files=True)
with col2:
    prod_files = st.file_uploader("Upload Product Images", type=["jpg", "png"], accept_multiple_files=True)

if st.button("🚀 EXECUTE FULL AUDIT", type="primary"):
    if doc_files and prod_files:
        with st.spinner('AI conducting 8-step inspection...'):
            try:
                res = perform_audit(doc_files, prod_files)

                # 1. SCORE & SUMMARY
                st.markdown(f"## Consistency Score: {res['consistency_score']}%")
                st.progress(res['consistency_score'] / 100)
                st.info(res['summary'])

                # 2. AI CONTEXT ANALYSIS
                st.markdown("### 📝 AI Context Analysis")
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**📄 Document Extraction**")
                    st.write(res.get('doc_description', 'N/A'))
                with c2:
                    st.markdown("**📦 Physical Observation**")
                    st.write(res.get('physical_description', 'N/A'))

                # 3. VERIFICATION TABLE
                st.markdown("### 📊 Verification Details")
                st.table(res['comparison'])

                # 4. AUDIT CHECKLIST
                st.markdown("### ✅ Detailed Audit Checklist")
                checklist = res.get('audit_checklist', {})
                data = [{"Step": k.replace('_', ' '), "Score": v} for k, v in checklist.items()]
                st.table(data)

                # 5. KEY ISSUES
                st.markdown("### 🔍 Key Issues & Discrepancies")
                for issue in res.get('key_issues', []):
                    st.warning(f"⚠️ {issue}")

                if res['consistency_score'] < 100:
                    st.markdown("---")
                    if st.button("Override and Force PASS"):
                        st.success("✅ Audit result manually overridden.")
            except Exception as e:
                st.error(f"Audit Error: {e}")
    else:
        st.warning("Please upload both documents and product images to proceed.")
