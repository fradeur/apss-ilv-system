import streamlit as st
from google import genai
from google.genai import types
import json

# ==========================================
# SYSTEM CONFIGURATION
# ==========================================
# Lấy API Key từ hệ thống Secrets của Streamlit
api_key = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=api_key)

st.set_page_config(page_title="APSS - Advanced Audit", layout="wide")

# ==========================================
# AI ENGINE: STRUCTURED AUDIT
# ==========================================
def perform_audit(doc_files, prod_files):
    # Prompt yêu cầu AI trả về cấu trúc JSON rõ ràng, cấm đoán mò và có barem chấm điểm
    prompt = """
    Perform an expert logistics audit. 
    CRITICAL RULE: Focus ONLY on validating the Item Identity (Part Number/Description) and Quantity. 
    DO NOT extract, guess, or evaluate Weight or Dimensions under any circumstances.
    
    SCORING RUBRIC for 'consistency_score':
    - 100: Perfect match in both Item Identity and Quantity. No extra undeclared items.
    - 50 to 99: Partial match (e.g., Item Identity matches, but Quantity is incorrect, or there are extra undeclared items alongside the correct ones).
    - 1 to 49: Severe discrepancy, but some parts match.
    - 0: Critical mismatch (completely wrong item, nothing matches the documentation).
    
    Return JSON strictly in this format:
    {
        "summary": "One sentence overall summary of the audit result.",
        "doc_description": "A brief summary of what the documents declare (Item and Quantity).",
        "physical_description": "A brief summary of what is visible in the physical product images (Item and Quantity).",
        "comparison": [
            {"Aspect": "Item Identity", "Doc": "...", "Physical": "..."}, 
            {"Aspect": "Quantity", "Doc": "...", "Physical": "..."}
        ],
        "consistency_score": 0,
        "key_issues": ["Issue 1", "Issue 2"]
    }
    """

    contents = [prompt]
    
    # Nạp file chứng từ vào AI
    for f in doc_files:
        contents.append(types.Part.from_bytes(data=f.read(), mime_type=f.type))
        
    # Nạp file hình ảnh thực tế vào AI
    for f in prod_files:
        contents.append(types.Part.from_bytes(data=f.read(), mime_type=f.type))

    # Gọi model xử lý với temperature = 0.0 để đảm bảo tính chính xác
    response = client.models.generate_content(
        model='models/gemini-2.5-flash',
        contents=contents,
        config=types.GenerateContentConfig(temperature=0.0)
    )

    # Làm sạch chuỗi trả về để parse JSON
    return json.loads(response.text.replace('```json', '').replace('```', '').strip())

# ==========================================
# WEB UI: DASHBOARD STYLE
# ==========================================
st.title("📦 APSS - Logistics Audit Dashboard")
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    doc_files = st.file_uploader("Upload Documents (PDF/Img)", type=["pdf", "jpg", "png"], accept_multiple_files=True)
with col2:
    prod_files = st.file_uploader("Upload Product Images", type=["jpg", "png"], accept_multiple_files=True)

if st.button("🚀 EXECUTE ADVANCED AUDIT", type="primary"):
    if doc_files and prod_files:
        with st.spinner('AI auditing in progress...'):
            try:
                res = perform_audit(doc_files, prod_files)

                # 1. SCORE & SUMMARY
                st.markdown(f"### Overall Consistency Score: {res['consistency_score']}%")
                st.progress(res['consistency_score'] / 100)
                st.info(res['summary'])

                # 2. AI CONTEXT ANALYSIS (Phần mô tả Context)
                st.markdown("### 📝 AI Context Analysis")
                colA, colB = st.columns(2)
                with colA:
                    st.markdown("**📄 Document Extraction**")
                    st.write(res.get('doc_description', 'No document description provided.'))
                with colB:
                    st.markdown("**📦 Physical Observation**")
                    st.write(res.get('physical_description', 'No physical description provided.'))

                # 3. VERIFICATION TABLE (Chỉ hiển thị Identity và Quantity)
                st.markdown("### 📊 Verification Details")
                st.table(res['comparison'])

                # 4. KEY ISSUES
                st.markdown("### 🔍 Key Issues & Discrepancies")
                if len(res.get('key_issues', [])) > 0:
                    for issue in res['key_issues']:
                        st.markdown(f"* ⚠️ {issue}")
                else:
                    st.success("✅ No discrepancies found. Physical item matches documentation perfectly!")

                # 5. MANUAL OVERRIDE
                if res['consistency_score'] < 100:
                    st.markdown("---")
                    if st.button("Override and Force PASS"):
                        st.success("✅ Audit result manually overridden by operator.")
            except Exception as e:
                st.error(f"Audit Error: {e}")
    else:
        st.warning("Please upload both documents and product images to proceed.")
