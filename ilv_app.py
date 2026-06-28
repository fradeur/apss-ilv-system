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
# Thay API KEY của ní vào đây
client = genai.Client(api_key="GEMINI_API_KEY") 
st.set_page_config(page_title="APSS - ILV System v2.0", page_icon="📦", layout="wide")

# ==========================================
# AI ENGINE: MULTIMODAL VERIFICATION
# ==========================================
def extract_data_from_image(img, hs_code_list):
    prompt = f"""
    You are a physical inventory inspection expert. Analyze the image and return a precise JSON:
    1. "extracted_codes": List of all part numbers visible on labels.
    2. "object_category": Description of items (e.g., 'steel pipe', 'rubber seal').
    3. "hs_code_hint": Match the visual object with these HS Codes: {hs_code_list}

    Required JSON format:
    {{
        "extracted_codes": [],
        "object_category": "",
        "hs_code_hint": ""
    }}
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash', # Phiên bản mới nhất
            contents=[img, prompt],
            config=types.GenerateContentConfig(temperature=0.0)
        )
        raw_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(raw_text)
    except Exception as e:
        st.error(f"AI Analysis Error: {e}")
        return None

# ==========================================
# WEB UI (FRONTEND)
# ==========================================
st.title("📦 Inbound Logistics Verifier (ILV) v2.0")
st.markdown("**Dual-Layer Security: Visual AI Engine + ERP Data Integration**")
st.divider()

col1, col2 = st.columns(2)
with col1:
    uploaded_excel = st.file_uploader("Upload 'APSS Purchase Lines' (.xlsx)", type=["xlsx"])
with col2:
    uploaded_image = st.file_uploader("Capture/Upload package image", type=["jpg", "jpeg", "png"])

if st.button("🚀 INITIATE DUAL-SCAN", use_container_width=True, type="primary"):
    if uploaded_excel and uploaded_image:
        # LOAD & SELECTIVE PARSING (Đọc trực tiếp Excel)
        cols_to_keep = ['Document No.', 'Description', 'Long Description', 'HS Code', 
                        'Vendor Name', 'Unit of Measure Code', 'Direct Unit Cost Excl. VAT', 
                        'No.', 'Document Type', 'Expected Receipt Date']
        
        df = pd.read_excel(uploaded_excel, engine='openpyxl')
        df = df[cols_to_keep] # Lọc cột
        
        # Tiền xử lý
        df['Expected Receipt Date'] = pd.to_datetime(df['Expected Receipt Date'], errors='coerce')
        df = df[df['Document Type'] == 'Order'] 
        
        img = Image.open(uploaded_image)
        st.image(img, caption="Actual Package Image", width=300)

        with st.spinner('Analyzing with AI...'):
            hs_codes = df['HS Code'].unique().tolist()
            ai_data = extract_data_from_image(img, hs_codes)
            
        if ai_data:
            st.subheader("👁️ LAYER 1: PHYSICAL SANITY CHECK")
            st.info(f"**Object Identified:** `{ai_data['object_category']}` | **HS Code Match:** `{ai_data['hs_code_hint']}`")

            st.subheader("📊 LAYER 2: FUZZY CODE MATCHING")
            
            # Ghi header cho file log nếu chưa có
            if not os.path.exists('audit_log.csv'):
                with open('audit_log.csv', 'w', newline='') as f:
                    csv.writer(f).writerow(['PO_Number', 'Status', 'Match_Ratio'])

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
                
                # AUTO-LOGGING
                with open('audit_log.csv', 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([po_code, status, best_ratio])

            st.success("✅ Logged to audit_log.csv")
            with open("audit_log.csv", "rb") as file:
                st.download_button("📥 Download Audit Report", file, "audit_log.csv")
    else:
        st.warning("Please upload Master Data and Image to proceed.")
