import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
from thefuzz import fuzz
from PIL import Image
import json

# ==========================================
# SYSTEM CONFIGURATION
# ==========================================
# INSERT YOUR API KEY HERE
client = genai.Client(api_key="AQ."GEMINI_API_KEY")
st.set_page_config(page_title="APSS - ILV System", page_icon="📦", layout="wide")


# ==========================================
# AI ENGINE: OCR & OBJECT RECOGNITION
# ==========================================
def extract_data_from_image(img):
    prompt = """
    You are a physical inventory inspection expert. Analyze the image and return a precise JSON:
    1. "extracted_codes": A list of all part numbers/codes visible on the labels.
    2. "object_category": A list describing EACH distinct physical object seen in the image.

    Required JSON format:
    {
        "extracted_codes": ["code_1", "code_2"],
        "object_category": ["black pipe", "blue boxes", "yellow metal parts"]
    }
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',  # Nếu lỗi 503 lại hiện, ní có thể đổi số 2.5 thành 1.5 nhé
            contents=[img, prompt],
            config=types.GenerateContentConfig(temperature=0.0)
        )
        raw_text = response.text.replace('```json', '').replace('```', '').strip()
        ai_data = json.loads(raw_text)

        codes = [str(c) for c in ai_data.get("extracted_codes", [])]

        # XỬ LÝ ĐA VẬT THỂ
        cat_list = ai_data.get("object_category", ["Unknown"])
        if isinstance(cat_list, list):
            obj_cat = ", ".join(cat_list)
        else:
            obj_cat = str(cat_list)

        # ĐÂY LÀ DÒNG CHÚNG TA ĐÃ LỠ TAY XÓA MẤT LÚC NÃY!
        return codes, obj_cat

    except Exception as e:
        st.error(f"AI Error: {e}")
        return [], "Extraction Failed"


# ==========================================
# FUZZY MATCHING ENGINE
# ==========================================
def fuzzy_match(po_dict, ai_codes, threshold=85):
    results = []
    # po_dict contains {Item Code: Item Description}
    for po_code, description in po_dict.items():
        best_code, highest_ratio = None, 0
        for ai_code in ai_codes:
            ratio = fuzz.ratio(po_code.upper(), ai_code.upper())
            if ratio > highest_ratio:
                highest_ratio = ratio
                best_code = ai_code

        if highest_ratio == 100:
            status, color = "GREEN - 100% Match", "success"
        elif highest_ratio >= threshold:
            status, color = f"YELLOW - {highest_ratio}% Match (Manual Verification Required)", "warning"
        else:
            status, color = "RED - Code Not Found", "error"

        results.append({
            "PO_Code": po_code,
            "Item_Description": description,
            "AI_Code": best_code if highest_ratio >= threshold else "N/A",
            "Status": status,
            "color_code": color
        })
    return results


# ==========================================
# WEB UI (FRONTEND)
# ==========================================
st.title("📦 Inbound Logistics Verifier (ILV) v2.0")
st.markdown("**Dual-Layer Security: Optical Character Recognition (OCR) & Physical Sanity Check**")
st.divider()

col1, col2 = st.columns(2)

with col1:
    st.header("1. ERP Data (Business Central)")
    uploaded_excel = st.file_uploader("Drag & drop BC PO Export Excel file here", type=["xlsx"])

with col2:
    st.header("2. Physical Warehouse")
    uploaded_image = st.file_uploader("Upload/Capture package image here", type=["jpg", "jpeg", "png"])

st.divider()

# ==========================================
# EXECUTION BLOCK
# ==========================================
if st.button("🚀 INITIATE DUAL-SCAN", use_container_width=True, type="primary"):
    if uploaded_excel is not None and uploaded_image is not None:

        with st.spinner('Loading data streams...'):
            df = pd.read_excel(uploaded_excel)
            df_clean = df[df['Type'] == 'Item']
            # Create a dictionary {Item No.: Description} from Excel
            po_dict = dict(zip(df_clean['No.'].astype(str), df_clean['Description'].astype(str)))

            img = Image.open(uploaded_image)
            st.image(img, caption="Actual Package Image", width=300)

        with st.spinner('AI visual analysis in progress...'):
            # Extract both codes and object category
            ai_found_list, ai_detected_object = extract_data_from_image(img)

        # DISPLAY LAYER 1 (SANITY CHECK)
        st.subheader("👁️ LAYER 1: PHYSICAL SANITY CHECK")
        st.info(f"**AI identified the object in the image as:** `[{ai_detected_object.upper()}]`")

        # DISPLAY LAYER 2 (FUZZY MATCH CODE)
        st.subheader("📊 LAYER 2: ITEM CODE FUZZY MATCHING")
        final_results = fuzzy_match(po_dict, ai_found_list, threshold=85)

        for res in final_results:
            # Compare BC Description with AI detected object
            cross_check_msg = f"*(BC Description: {res['Item_Description']} ➔ AI Vision: {ai_detected_object})*"

            if res['color_code'] == "success":
                st.success(f"✅ **Code {res['PO_Code']}** ➔ {res['Status']} | {cross_check_msg}")
            elif res['color_code'] == "warning":
                st.warning(
                    f"⚠️ **Code {res['PO_Code']}** ➔ AI Read: {res['AI_Code']} | {res['Status']} | {cross_check_msg}")
            else:
                st.error(f"❌ **Code {res['PO_Code']}** ➔ {res['Status']} | {cross_check_msg}")

    else:
        st.error("Please upload both the Excel file and the Package Image to initialize the system.")