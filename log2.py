import streamlit as st
from google import genai
from google.genai import types
import json

# ==========================================
# SYSTEM CONFIGURATION
# ==========================================
client = genai.Client(api_key="GEMINI_API_KEY")
st.set_page_config(page_title="APSS - Advanced Audit", layout="wide")


# ==========================================
# AI ENGINE: STRUCTURED AUDIT
# ==========================================
def perform_audit(doc_files, prod_files):
    # Prompt yêu cầu AI trả về cấu trúc rõ ràng
    prompt = """
    Perform an expert logistics audit. Return JSON strictly:
    {
        "summary": "One sentence summary of the shipment.",
        "comparison": [{"Aspect": "Quantity", "Doc": "...", "Physical": "..."}, {"Aspect": "Dimensions", "Doc": "...", "Physical": "..."}, {"Aspect": "Weight", "Doc": "...", "Physical": "..."}],
        "consistency_score": 0,
        "key_issues": ["Issue 1", "Issue 2", "Issue 3"]
    }
    """

    contents = [prompt]
    for f in doc_files:
        contents.append(types.Part.from_bytes(data=f.read(), mime_type=f.type))
    for f in prod_files:
        contents.append(types.Part.from_bytes(data=f.read(), mime_type=f.type))

    response = client.models.generate_content(
        model='models/gemini-3-pro-image',
        contents=contents,
        config=types.GenerateContentConfig(temperature=0.0)
    )

    return json.loads(response.text.replace('```json', '').replace('```', '').strip())


# ==========================================
# WEB UI: DASHBOARD STYLE
# ==========================================
st.title("📦 APSS - Logistics Audit Dashboard")

col1, col2 = st.columns(2)
with col1:
    doc_files = st.file_uploader("Upload Documents", type=["pdf", "jpg", "png"], accept_multiple_files=True)
with col2:
    prod_files = st.file_uploader("Upload Product Images", type=["jpg", "png"], accept_multiple_files=True)

if st.button("🚀 EXECUTE ADVANCED AUDIT", type="primary"):
    if doc_files and prod_files:
        with st.spinner('AI auditing...'):
            try:
                res = perform_audit(doc_files, prod_files)

                # 1. SCORE
                st.markdown(f"### Overall Consistency Score: {res['consistency_score']}%")
                st.progress(res['consistency_score'] / 100)
                st.info(res['summary'])

                # 2. BẢNG SO SÁNH
                st.markdown("### 📊 Verification Details")
                st.table(res['comparison'])

                # 3. DANH SÁCH LỖI
                st.markdown("### 🔍 Key Issues & Discrepancies")
                for issue in res['key_issues']:
                    st.markdown(f"* ⚠️ {issue}")

                # Manual Override
                if res['consistency_score'] < 100:
                    if st.button("Override and Force PASS"):
                        st.success("✅ Audit result manually overridden.")
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.warning("Please upload both documents and product images.")
