import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
from thefuzz import fuzz
from PIL import Image
import json
import csv
import os

# ==========================================
# SYSTEM CONFIGURATION
# ==========================================
client = genai.Client(api_key="GEMINI_API_KEY") # Thay API KEY của ní vào đây
st.set_page_config(page_title="APSS - ILV System v2.0", page_icon="📦", layout="wide")

# ==========================================
# AI ENGINE: MULTIMODAL VERIFICATION
# ==========================================
def extract_data_from_image(img, po_data_sample):
    # Nâng cấp Prompt: Nhúng cả HS Code vào để AI đối chiếu
    hs_codes = po_data_sample['HS Code'].unique().tolist()
    prompt = f"""
    You are a physical inventory inspection expert. Analyze the image and return a precise JSON:
    1. "extracted_codes": List of all part numbers/codes visible on labels.
    2. "object_category": Description of items (e.g., 'steel pipe', 'rubber seal').
    3. "hs_code_hint": Match the visual object with these HS Codes: {hs_codes}

    Required JSON format:
    {{
        "extracted_codes": [],
        "object_category": "",
        "hs_code_hint": ""
    }}
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[img, prompt],
            config=types.GenerateContentConfig(temperature=0.0)
        )
        raw_text = response.text.replace('```json', '').replace('```', '').strip()
        ai_data = json.loads(raw_text)
        return ai_data
    except Exception as e:
        st.error(f"AI Analysis Error: {e}")
        return None

# ==========================================
# WEB UI
# ==========================================
st.title("📦 Inbound Logistics Verifier (ILV) v2.0")
st.markdown("**Dual-Layer Security: Visual AI Engine + ERP Data Integration**")
st.divider()

col1, col2 = st.columns(2)
with col1:
    uploaded_excel = st.file_uploader("Upload 'APSS Purchase Lines' Master Data (.csv)", type=["csv"])
with col2:
    uploaded_image = st.file_uploader("Capture/Upload package image", type=["jpg", "jpeg", "png"])

if st.button("🚀 INITIATE DUAL-SCAN", use_container_width=True, type="primary"):
    if uploaded_excel and uploaded_image:
        # Load & Clean Data
        df = pd.read_csv(uploaded_excel)
        df = df[df['Document Type'] == 'Order'] # Chỉ lấy đơn hàng chờ nhập
        
        img = Image.open(uploaded_image)
        st.image(img, caption="Actual Package Image", width=300)

        with st.spinner('Analyzing with AI...'):
            ai_data = extract_data_from_image(img, df)
            
        if ai_data:
            st.subheader("👁️ LAYER 1: PHYSICAL SANITY CHECK")
            st.info(f"**Object Identified:** `{ai_data['object_category']}` | **HS Code Match:** `{ai_data['hs_code_hint']}`")

            st.subheader("📊 LAYER 2: FUZZY CODE MATCHING")
            for po_code in df['No.'].unique():
                best_ratio = 0
                for ai_code in ai_data['extracted_codes']:
                    ratio = fuzz.ratio(str(po_code).upper(), str(ai_code).upper())
                    best_ratio = max(best_ratio, ratio)
                
                # Logic hiển thị
                color = "success" if best_ratio == 100 else ("warning" if best_ratio >= 85 else "error")
                status = "PASS" if best_ratio == 100 else ("WARNING" if best_ratio >= 85 else "REJECT")
                
                msg = f"**Code {po_code}** ➔ {status} ({best_ratio}%)"
                if color == "success": st.success(msg)
                elif color == "warning": st.warning(msg)
                else: st.error(msg)
                
                # AUTO-LOGGING (Lưu vết tự động cho báo cáo cuối tháng)
                with open('audit_log.csv', 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([po_code, status, best_ratio])

            st.success("✅ Logged to audit_log.csv")
            with open("audit_log.csv", "rb") as file:
                st.download_button("📥 Download Audit Report", file, "audit_log.csv")
    else:
        st.warning("Please upload Master Data and Image to proceed.")
