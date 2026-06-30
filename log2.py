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
    # Prompt áp dụng Cơ chế Trọng số (40-40-20) với Độ mịn cao (High Granularity)
    prompt = """
    Perform an expert logistics audit. 
    CRITICAL RULE: Focus ONLY on validating the Item Identity (Part Number/Description) and Quantity. 
    DO NOT extract, guess, or evaluate Weight or Dimensions under any circumstances.
    
    WEIGHTED SCORING SYSTEM (Total: 100 points - Calculate with high granularity, allowing exact odd/decimal-like integer scores such as 27, 34, 42, etc.):
    1. Item Identity (Max 40 pts): Award 40 pts for a perfect match. Deduct partial points if the name is slightly off but part number is correct. Award 0 only if completely wrong.
    2. Quantity (Max 40 pts): Award 40 pts for a perfect match. Calculate a precise mathematical penalty based on the deviation ratio (e.g., if actual is 5x the declared, do not just give 0, calculate a granular partial score reflecting the severe ratio).
    3. Extras & Labeling (Max 20 pts): Award 20 pts for perfect status. Deduct exact points dynamically depending on the severity and number of misleading labels found.
    
    CRITICAL: Do not round the final score to the nearest 5 or 10. Compute a precise, custom integer score based on the exact evaluation.
    
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

    # Gọi model xử lý với temperature = 0.0 để đảm bảo tính logic và toán học chặt chẽ nhất
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

                # 2. AI CONTEXT ANALYSIS
                st.markdown("### 📝 AI Context Analysis")
                colA, colB = st.columns(2)
                with colA:
                    st.markdown("**📄 Document Extraction**")
                    st.write(res.get('doc_description', 'No document description provided.'))
                with colB:
                    st.markdown("**📦 Physical Observation**")
                    st.write(res.get('physical_description', 'No physical description provided.'))

                # 3. VERIFICATION TABLE
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
