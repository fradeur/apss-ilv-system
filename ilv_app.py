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
# CẤU HÌNH HỆ THỐNG
# ==========================================
client = genai.Client(api_key="GEMINI_API_KEY")  # Ní nhớ điền API KEY của ní vào đây
st.set_page_config(page_title="APSS - ILV System v2.0", page_icon="📦", layout="wide")


# ==========================================
# AI ENGINE: MULTIMODAL VERIFICATION
# ==========================================
def extract_data_from_image(img, hs_code_list):
    # Prompt chuyên sâu cho chuyên gia kho bãi
    prompt = f"""
    Analyze the image and return a JSON with:
    1. "extracted_codes": List of codes found on labels.
    2. "object_category": Description (e.g. steel pipe).
    3. "hs_code_hint": Match with these HS Codes: {hs_code_list}
    """
    try:
        response = client.models.generate_content(
            model='models/gemini-3.5-flash',
            contents=[img, prompt],
            config=types.GenerateContentConfig(temperature=0.0)
        )
        raw_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(raw_text)
    except Exception as e:
        # CHẾ ĐỘ GIẢ LẬP (FALL-BACK) NẾU HẾT QUOTA
        st.warning("⚠️ Quota hết! Đang dùng chế độ Demo giả lập...")
        return {
            "extracted_codes": ["APSS-PO-2308-0059"],
            "object_category": "Simulated Steel Pipe",
            "hs_code_hint": hs_code_list[0] if hs_code_list else "N/A"
        }


# ==========================================
# WEB UI
# ==========================================
st.title("📦 Inbound Logistics Verifier (ILV) v2.0")
st.markdown("**Hệ thống đối chiếu tự động: AI Vision + Business Central Data**")
st.divider()

col1, col2 = st.columns(2)
with col1:
    uploaded_excel = st.file_uploader("Upload 'APSS Purchase Lines' (.xlsx)", type=["xlsx"])
with col2:
    uploaded_images = st.file_uploader("Upload ảnh kiện hàng (có thể chọn nhiều)",
                                       type=["jpg", "jpeg", "png"],
                                       accept_multiple_files=True)

if st.button("🚀 BẮT ĐẦU QUÉT HÀNG LOẠT", use_container_width=True, type="primary"):
    if uploaded_excel and uploaded_images:
        # LOAD DỮ LIỆU
        df = pd.read_excel(uploaded_excel, engine='openpyxl')
        df = df[df['Document Type'] == 'Order']  # Lọc đơn chờ nhập
        hs_codes = df['HS Code'].unique().tolist()

        # VÒNG LẶP XỬ LÝ ẢNH
        for img_file in uploaded_images:
            st.divider()
            st.subheader(f"📸 Phân tích: {img_file.name}")

            img = Image.open(img_file)
            st.image(img, width=200)

            with st.spinner('AI đang kiểm tra...'):
                ai_data = extract_data_from_image(img, hs_codes)

            if ai_data:
                st.info(f"**Đối tượng:** `{ai_data['object_category']}` | **HS Code:** `{ai_data['hs_code_hint']}`")

                # SO KHỚP DỮ LIỆU
                for po_code in df['No.'].unique():
                    best_ratio = 0
                    for ai_code in ai_data['extracted_codes']:
                        ratio = fuzz.ratio(str(po_code).upper(), str(ai_code).upper())
                        best_ratio = max(best_ratio, ratio)

                    status = "PASS" if best_ratio == 100 else ("WARNING" if best_ratio >= 85 else "REJECT")

                    if status == "PASS":
                        st.success(f"✅ {po_code}: {status} ({best_ratio}%)")
                    elif status == "WARNING":
                        st.warning(f"⚠️ {po_code}: {status} ({best_ratio}%)")
                    else:
                        st.error(f"❌ {po_code}: {status} ({best_ratio}%)")

                    # GHI LOG
                    with open('audit_log.csv', 'a', newline='') as f:
                        csv.writer(f).writerow([img_file.name, po_code, status, best_ratio])

        st.success("✅ Đã hoàn tất! Dữ liệu đã được log.")
        with open("audit_log.csv", "rb") as file:
            st.download_button("📥 Tải báo cáo Audit", file, "audit_log.csv")
    else:
        st.warning("Vui lòng tải cả File Excel và Ảnh kiện hàng!")