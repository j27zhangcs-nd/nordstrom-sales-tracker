import streamlit as st
import pandas as pd
import os
import time
import gspread
import pytz
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- 1. 页面配置 ---
st.set_page_config(page_title="Nordstrom Sales Tracker", page_icon="💄", layout="centered")

if 'entry_key' not in st.session_state:
    st.session_state.entry_key = 0

# 🔥🔥🔥 魔法 UI 样式区 (CSS) 🔥🔥🔥
def add_custom_css():
    st.markdown("""
    <style>
    html, body, [class*="css"] { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; }
    
    /* --- 1. Radio (单选) 基础样式 --- */
    div[role="radiogroup"] label > div:first-child { display: none !important; }
    div[role="radiogroup"] label {
        background-color: #f8f9fa;
        padding: 10px 5px;
        border-radius: 8px;
        border: 1px solid #eee;
        margin: 0 !important;
        display: flex;
        justify-content: center;
        align-items: center;
        cursor: pointer;
        transition: all 0.2s ease;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        color: #555;
        font-weight: 500;
        font-size: 13px; 
        height: 100% !important;
        width: 100%;
        text-align: center !important;
        white-space: pre-wrap !important; 
        line-height: 1.3 !important; 
    }
    
    /* 选中状态 */
    div[role="radiogroup"] label:has(input:checked) {
        background-color: #FFF0F5 !important;
        color: #9F1239 !important;
        border: 1px solid #FDA4AF !important;
        box-shadow: 0 2px 5px rgba(253, 164, 175, 0.4);
        font-weight: bold;
    }

    /* --- 2. 核心优化：强制让顶部两组按钮等大 --- */
    /* 我们使用模糊匹配 [aria-label*="..."] 来规避特殊字符导致的失效问题 */
    div[role="radiogroup"][aria-label*="Outcome"] label, 
    div[role="radiogroup"][aria-label*="Lanc"] label { 
        min-height: 85px !important; /* 强制锁定高度 */
        padding: 15px 10px !important; 
        font-size: 16px !important; 
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    /* --- 3. Checkbox (多选) 样式 --- */
    div[data-testid="stCheckbox"] label > span:first-child { display: none !important; }
    div[data-testid="stCheckbox"] {
        background-color: #f8f9fa;
        padding: 10px 5px;
        border-radius: 8px;
        border: 1px solid #eee;
        transition: all 0.2s ease;
        text-align: center;
        cursor: pointer;
        height: 100%;
        display: flex;
        justify-content: center;
        align-items: center;
        white-space: pre-wrap !important;
        line-height: 1.3 !important;
    }
    
    div[data-testid="stCheckbox"]:has(input:checked) {
        background-color: #FFF0F5 !important;
        color: #9F1239 !important;
        border: 1px solid #FDA4AF !important;
        box-shadow: 0 2px 5px rgba(253, 164, 175, 0.4);
        font-weight: bold;
    }

    /* --- 4. Grid 布局适配手机 --- */
    div[role="radiogroup"] { display: grid !important; gap: 10px !important; }
    
    /* 2 列显示的组 */
    div[role="radiogroup"][aria-label*="Outcome"], 
    div[role="radiogroup"][aria-label*="Lanc"],
    div[role="radiogroup"][aria-label="Race"],
    div[role="radiogroup"][aria-label="Gender"],
    div[role="radiogroup"][aria-label="Type"],
    div[role="radiogroup"][aria-label="Intent"],
    div[role="radiogroup"][aria-label="Contact"],
    div[role="radiogroup"][aria-label="Service Duration"] { 
        grid-template-columns: 1fr 1fr !important; 
    }

    /* 3 列显示的组 */
    div[role="radiogroup"][aria-label="Age"],
    div[role="radiogroup"][aria-label="Reason"] { 
        grid-template-columns: repeat(3, 1fr) !important; 
    }

    .stNumberInput, .stSelectbox { margin-top: -5px; }
    </style>
    """, unsafe_allow_html=True)

add_custom_css()

# --- 2. Google Sheets 连接 ---
@st.cache_resource
def get_google_sheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    if os.path.exists("secrets.json"):
        creds = ServiceAccountCredentials.from_json_keyfile_name("secrets.json", scope)
    else:
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open("Nordstrom Sales Data").sheet1 
    return sheet

def get_seattle_time():
    utc_now = datetime.now(pytz.utc)
    seattle_tz = pytz.timezone('America/Los_Angeles')
    return utc_now.astimezone(seattle_tz)

def save_data(data):
    sheet = get_google_sheet()
    def clean(val): return val if val is not None else ""
    promo_str = ", ".join(data.get("Promo", [])) if isinstance(data.get("Promo"), list) else str(data.get("Promo", ""))
    lc_str = ", ".join(data.get("Lancome_Cats", [])) if isinstance(data.get("Lancome_Cats"), list) else str(data.get("Lancome_Cats", ""))
    row = [
        data["Time"], clean(data["Age"]), clean(data["Gender"]), clean(data["Race"]),
        clean(data["Intent"]), clean(data["Outcome"]), data["Amount"], clean(data["Reason"]),
        clean(data["Type"]), promo_str, clean(data["Contact"]),
        clean(data.get("Is_Lancome")), lc_str, clean(data.get("Duration"))
    ]
    sheet.append_row(row)

def load_data():
    try:
        sheet = get_google_sheet()
        return pd.DataFrame(sheet.get_all_records())
    except: return pd.DataFrame()

# --- 3. 页面主逻辑 ---
st.title("💄 Nordstrom Beauty Tracker")

with st.spinner('Loading data...'):
    df_all = load_data()

seattle_now = get_seattle_time()
today_str = seattle_now.strftime("%Y-%m-%d")

# 统计今日业绩
total_sales_today = 0
if not df_all.empty and 'Time' in df_all.columns:
    df_today = df_all[df_all['Time'].astype(str).str.startswith(today_str)].copy()
    if not df_today.empty:
        df_today['Amount'] = pd.to_numeric(df_today['Amount'], errors='coerce').fillna(0)
        total_sales_today = df_today['Amount'].sum()

tab1, tab2 = st.tabs(["📝 Entry 数据录入", "📊 Dashboard 统计看板"])

with tab1:
    st.metric("今日业绩 Today's Sales", f"${total_sales_today:,.0f}")
    st.divider()

    k = str(st.session_state.entry_key)

    # 1. 结果选择
    outcome_mode = st.radio(
        "Outcome Mode", 
        ["✅ Bought\n买了", "❌ No Buy\n没买"], 
        horizontal=True, 
        label_visibility="collapsed",
        index=None,
        key="outcome_" + k  
    )
    st.write("") 

    if outcome_mode:
        # 2. 品牌选择
        is_lancome = "N/A"
        if "Bought" in outcome_mode:
            is_lancome = st.radio("Is Lancôme?", ["Yes\n是", "No\n否"], horizontal=True, index=None, key="is_lancome_" + k)
        
        # 3. 数据录入表单
        with st.form("entry_form", clear_on_submit=True):
            intent = None
            promo_selected = []
            contact = None
            lancome_cats_selected = []

            if "Bought" in outcome_mode:
                amount = st.number_input("Amount ($)", min_value=0.0, step=10.0, value=None, placeholder="0.00") 
                if is_lancome == "Yes\n是":
                    st.caption("Lancôme Categories")
                    lc1, lc2 = st.columns(2)
                    with lc1:
                        if st.checkbox("💄 Makeup\n彩妆"): lancome_cats_selected.append("Makeup")
                        if st.checkbox("🌸 Fragrance\n香水"): lancome_cats_selected.append("Fragrance")
                    with lc2:
                        if st.checkbox("🧴 Skincare\n护肤"): lancome_cats_selected.append("Skincare")
            else:
                amount = 0.0
                reason = st.radio("Reason", ["👀 Just Looking\n闲逛", "💰 Price\n太贵", "💄 Competitor\n竞品", "📦 Out of Stock\n缺货", "❓ Other\n其他"], horizontal=True, index=None)
            
            st.divider()
            st.caption("👤 Customer Profile")
            age = st.radio("Age", ["🐣 Youth\n青年", "👩 Mid-aged\n中年", "👵 Senior\n老年"], horizontal=True, index=None)
            
            c_gender, c_type = st.columns(2)
            with c_gender: gender = st.radio("Gender", ["👩 Female\n女", "👨 Male\n男"], horizontal=True, index=None)
            with c_type: customer_type = st.radio("Type", ["🆕 New\n我的新客", "🔁 Repeat\n我的回头客"], horizontal=True, index=None)
            
            race = st.radio("Race", ["⚪ White\n白人", "🐼 Chinese\n华人", "🌏 Asian\n亚裔", "🦅 Other US\n美国其他族裔", "🌍 Others\n其他"], horizontal=True, index=None)
            
            if "Bought" in outcome_mode:
                st.divider()
                st.caption("🤝 Interaction")
                intent = st.radio("Intent", ["👀 Browsing\n闲逛", "🎯 Target\n明确目标", "🎁 Pickup/Gift\n取货/礼物", "🔄 Return\n退换货"], horizontal=True, index=None)
                
                st.caption("Promo Method (可多选)")
                pm1, pm2 = st.columns(2)
                with pm1:
                    if st.checkbox("🗣️ Service\n专业推荐"): promo_selected.append("Service")
                    if st.checkbox("📉 Match\n比价/PM"): promo_selected.append("Price Match")
                    if st.checkbox("📅 Event\n商场活动"): promo_selected.append("Event")
                with pm2:
                    if st.checkbox("🎁 GWP\n赠品/小样"): promo_selected.append("GWP")
                    if st.checkbox("🛒 Grab&Go\n自助/无"): promo_selected.append("Grab & Go")
                
                contact = st.radio("Contact", ["🆕 New\n新抓取", "📂 Existing\n已有", "❌ No\n未留"], horizontal=True, index=None)

            st.divider() 
            st.caption("⏱️ Efficiency")
            duration = st.radio("Service Duration", ["⚡ < 5 min", "🕒 5-15 min", "⏳ 15-30 min", "🐢 > 30 min"], horizontal=True, index=None)

            submitted = st.form_submit_button("🚀 Submit (提交)", use_container_width=True)
            if submitted:
                save_data({
                    "Time": get_seattle_time().strftime("%Y-%m-%d %H:%M:%S"), 
                    "Age": age, "Gender": gender, "Race": race, "Intent": intent, 
                    "Outcome": outcome_mode, "Amount": amount or 0.0, "Reason": reason if "Bought" not in outcome_mode else "",
                    "Type": customer_type, "Promo": promo_selected, "Contact": contact,
                    "Is_Lancome": is_lancome, "Lancome_Cats": lancome_cats_selected, "Duration": duration
                })
                st.toast("✅ Saved!")
                time.sleep(0.5)
                st.session_state.entry_key += 1
                st.rerun()
    else:
        st.info("👆 Please select an outcome to start.")

# Tab 2 Dashboard 部分逻辑 (建议保留你原始代码中的部分)
# ====================
# TAB 2: 复盘模式
# ====================
with tab2:
    st.header("📊 Dashboard")
    col_date, col_space = st.columns([2, 1])
    with col_date:
        selected_date = st.date_input("📅 Date", value=seattle_now.date())
    
    selected_date_str = selected_date.strftime("%Y-%m-%d")
    is_viewing_today = (selected_date_str == today_str)

    df_view = pd.DataFrame()
    if not df_all.empty and 'Time' in df_all.columns:
        df_view = df_all[df_all['Time'].astype(str).str.startswith(selected_date_str)].copy()
    
    view_sales = 0; view_count = 0; view_conversion = 0
    if not df_view.empty:
        if 'Amount' in df_view.columns:
            df_view['Amount'] = pd.to_numeric(df_view['Amount'], errors='coerce').fillna(0)
        view_sales = df_view['Amount'].sum()
        view_count = len(df_view)
        view_bought_df = df_view[df_view['Outcome'].str.contains("Bought", na=False)]
        if view_count > 0:
            view_conversion = (len(view_bought_df) / view_count) * 100

    st.caption(f"Viewing Data: {selected_date_str}")
    m1, m2, m3 = st.columns(3)
    m1.metric("Sales", f"${view_sales:,.0f}")
    m2.metric("Traffic", f"{view_count}")
    m3.metric("Conv. Rate", f"{view_conversion:.0f}%")
    
    st.divider()

    if not df_view.empty:
        st.subheader("📈 Trends")
        try:
            chart_data = df_view.groupby("Intent")["Amount"].sum()
            st.bar_chart(chart_data)
        except:
            st.caption("No chart data")
            
        if 'Contact' in df_view.columns:
             contact_new = df_view[df_view['Contact'].astype(str).str.contains("New", na=False)].shape[0]
             st.caption(f"📱 Contact Capture: New {contact_new}")

        st.divider()
        
        if is_viewing_today:
            st.subheader("📜 Edit")
            col_undo, col_space2 = st.columns([1, 2])
            with col_undo:
                if st.button("↩️ Undo Last", type="primary"):
                    with st.spinner("Deleting..."):
                        success = delete_last_entry()
                    if success:
                        st.toast("✅ Deleted")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Error")
        else:
            st.info("History data is read-only.")

        st.dataframe(df_view.iloc[::-1], use_container_width=True)
    else:
        st.info(f"No records for {selected_date_str}")