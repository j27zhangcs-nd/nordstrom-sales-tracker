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

# 🔥🔥🔥 魔法 UI 样式区 (CSS) 🔥🔥🔥
def add_custom_css():
    st.markdown("""
    <style>
    html, body, [class*="css"] { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; }
    
    /* --- 1. Radio (单选) 样式 --- */
    div[role="radiogroup"] label > div:first-child { display: none !important; }
    div[role="radiogroup"] label {
        background-color: #f8f9fa;
        padding: 10px 5px;
        border-radius: 8px; /* 圆角稍微大一点，更有现代感 */
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
        height: 100%;
        width: 100%;
        text-align: center !important;
        
        /* 🔥 关键修改：支持换行符，且居中 🔥 */
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

    /* --- 2. Checkbox (多选) 伪装成按钮样式 --- */
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
        
        /* 🔥 关键修改：Checkbox 也要支持换行和居中 */
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
    
    div[role="radiogroup"] label:hover, div[data-testid="stCheckbox"]:hover { 
        border-color: #FECDD3; color: #9F1239; 
    }

    /* --- 3. Grid 布局控制 --- */
    div[role="radiogroup"] { display: grid !important; gap: 8px !important; }
    
    /* Outcome: 2列 */
    div[role="radiogroup"][aria-label="Outcome Mode"] { grid-template-columns: 1fr 1fr !important; }
    div[aria-label="Outcome Mode"] label { padding: 15px 10px !important; font-size: 15px !important; }

    /* Age/Race: 5列 */
    div[role="radiogroup"][aria-label="Age"] { grid-template-columns: repeat(5, 1fr) !important; }
    div[role="radiogroup"][aria-label="Race"] { grid-template-columns: repeat(5, 1fr) !important; }

    /* Gender/Type: 2列 */
    div[role="radiogroup"][aria-label="Gender"] { grid-template-columns: repeat(2, 1fr) !important; }
    div[role="radiogroup"][aria-label="Type"] { grid-template-columns: repeat(2, 1fr) !important; }
    
    /* Intent/Reason/Contact: 3列 */
    div[role="radiogroup"][aria-label="Intent"] { grid-template-columns: repeat(3, 1fr) !important; }
    div[role="radiogroup"][aria-label="Reason"] { grid-template-columns: repeat(3, 1fr) !important; }
    div[role="radiogroup"][aria-label="Contact"] { grid-template-columns: repeat(3, 1fr) !important; }

    .stNumberInput, .stSelectbox { margin-top: -5px; }
    </style>
    """, unsafe_allow_html=True)

add_custom_css()

# --- 2. Google Sheets 连接配置 ---
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

# --- 🕒 西雅图时间 ---
def get_seattle_time():
    utc_now = datetime.now(pytz.utc)
    seattle_tz = pytz.timezone('America/Los_Angeles')
    return utc_now.astimezone(seattle_tz)

# --- 数据处理 ---
def save_data(data):
    sheet = get_google_sheet()
    
    # 辅助函数：把 None 转换成空字符串，防止报错
    def clean(val):
        return val if val is not None else ""

    # Promo 是列表，需要特殊处理
    promo_val = data["Promo"]
    if promo_val is None:
        promo_str = ""
    elif isinstance(promo_val, list):
        promo_str = ", ".join(promo_val)
    else:
        promo_str = str(promo_val)

    row = [
        data["Time"], 
        clean(data["Age"]), clean(data["Gender"]), clean(data["Race"]),
        clean(data["Intent"]), clean(data["Outcome"]), 
        data["Amount"], clean(data["Reason"]),
        clean(data["Type"]),      
        promo_str,         
        clean(data["Contact"])    
    ]
    sheet.append_row(row)

def delete_last_entry():
    try:
        sheet = get_google_sheet()
        all_values = sheet.get_all_values()
        if len(all_values) > 1:
            sheet.delete_rows(len(all_values))
            return True
        else:
            return False
    except Exception as e:
        return False

def load_data():
    try:
        sheet = get_google_sheet()
        records = sheet.get_all_records()
        return pd.DataFrame(records)
    except Exception:
        return pd.DataFrame()

# --- 3. 侧边栏 ---
with st.sidebar:
    st.header("⚙️ Settings")
    daily_goal = st.number_input("🎯 今日目标Daily Goal ($)", value=1500, step=100)
    seattle_now = get_seattle_time()
    st.caption(f"📍 Seattle Time: {seattle_now.strftime('%H:%M')}")

# --- 4. 主逻辑 ---
st.title("💄 Nordstrom Beauty Tracker")

# 1️⃣ 加载数据
df_all = load_data()

# 2️⃣ 今日数据
today_str = seattle_now.strftime("%Y-%m-%d")
total_sales_today = 0
if not df_all.empty and 'Time' in df_all.columns:
    df_today_only = df_all[df_all['Time'].astype(str).str.startswith(today_str)].copy()
    if not df_today_only.empty:
        df_today_only['Amount'] = pd.to_numeric(df_today_only['Amount'], errors='coerce').fillna(0)
        total_sales_today = df_today_only['Amount'].sum()

# Tab 分页
tab1, tab2 = st.tabs(["📝 Entry 数据录入", "📊 Dashboard 统计看板"])

# ====================
# TAB 1: 战斗模式
# ====================
with tab1:
    st.metric("今日业绩 Today's Sales", f"${total_sales_today:,.0f}", f"Goal: ${daily_goal} ({(total_sales_today/daily_goal)*100:.0f}%)")
    st.progress(min(total_sales_today / daily_goal, 1.0))
    st.divider()

    # 🔥 1. 结果选择 (index=None 实现不预选)
    # 注意文本中间的 \n，这是实现换行的关键
    outcome_mode = st.radio(
        "Outcome Mode", 
        ["✅ Bought\n买了", "❌ No Buy\n没买"], 
        horizontal=True, 
        label_visibility="collapsed",
        index=None  # <--- 没有任何默认值
    )
    st.write("") 

    # 🔥 2. 只有当用户选择了 Outcome 后，才显示下面的表单
    if outcome_mode is None:
        st.info("👆 Please select an outcome to start recording.\n(请先点击上方“买了”或“没买”开始录入)")
    
    else:
        # 进入表单区域
        with st.form("entry_form", clear_on_submit=True):
            
            # --- 金额 / 原因 ---
            if "Bought" in outcome_mode:
                amount = st.number_input("Amount ($)", min_value=0.0, step=10.0, value=None, placeholder="0.00")
                reason = "" 
            else:
                amount = 0.0
                reason = st.radio("Reason", 
                    ["👀 Just Looking\n闲逛", "💰 Price\n太贵", "💄 Competitor\n竞品", "📦 Out of Stock\n缺货", "❓ Other\n其他"], 
                    horizontal=True,
                    index=None # 不预选
                )
            
            st.divider()
            st.caption("👤 Customer Profile (顾客画像)")
            
            # 年龄 / 性别 / 类型 / 种族 -> 全都不预选 (index=None)
            # 文本格式：Emoji English \n Chinese
            age = st.radio("Age", ["🐣 Youth\n青年", "👩 Mid-aged\n中年", "👵 Senior\n老年"], horizontal=True, index=None)
            st.write("") 
            
            c_gender, c_type = st.columns(2)
            with c_gender:
                gender = st.radio("Gender", ["👩 Female\n女", "👨 Male\n男"], horizontal=True, index=None)
            with c_type:
                customer_type = st.radio("Type", ["🆕 New\n我的新客", "🔁 Repeat\n我的回头客"], horizontal=True, index=None)
            
            st.write("")
            race = st.radio("Race", ["⚪ White\n白人", "🐼 Chinese\n华人", "🌏 Asian\n亚裔", "🦅 Other US\n美国其他族裔", "🌍 Others\n其他"], horizontal=True, index=None)
            
            st.divider()
            st.caption("🤝 Interaction (交互过程)")

            intent = st.radio("Intent", 
                ["👀 Browsing\n闲逛", "🎯 Target\n明确目标", "🎁 Pickup/Gift\n取货/礼物", "🔄 Return\n退换货"], 
                horizontal=True,
                index=None
            )
            st.write("")
            
            st.caption("Promo Method (可多选)")
            # 促单方式：手动布局多选框
            promo_selected = []
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.checkbox("🗣️ Service\n专业推荐"): promo_selected.append("Service")
            with c2:
                if st.checkbox("🎁 GWP\n赠品/小样"): promo_selected.append("GWP")
            with c3:
                if st.checkbox("📉 Match\n比价/PM"): promo_selected.append("Price Match")
                
            c4, c5, c6 = st.columns(3)
            with c4:
                if st.checkbox("🛒 Grab&Go\n自助/无"): promo_selected.append("Grab & Go")
            with c5:
                if st.checkbox("📅 Event\n商场活动"): promo_selected.append("Event")
            with c6:
                st.empty() 

            st.write("")

            contact = st.radio("Contact", 
                ["🆕 New\n新抓取", "📂 Existing\n已有", "❌ No\n未留"], 
                horizontal=True,
                index=None
            )

            st.write("")
            st.write("")
            
            submit_label = "🚀 Submit (提交)" if "Bought" in outcome_mode else "📝 Record (记录)"
            
            if st.form_submit_button(submit_label, use_container_width=True):
                current_time_str = get_seattle_time().strftime("%Y-%m-%d %H:%M:%S")
                final_amount = amount if amount is not None else 0.0
                
                # 如果没选促单方式，默认给一个 "None"
                final_promo = promo_selected if promo_selected else ["None"]
                
                new_entry = {
                    "Time": current_time_str, 
                    "Age": age, "Gender": gender, "Race": race,
                    "Intent": intent, "Outcome": outcome_mode, 
                    "Amount": final_amount, "Reason": reason,
                    "Type": customer_type,
                    "Promo": final_promo, 
                    "Contact": contact
                }
                save_data(new_entry)
                st.toast("✅ Saved!")
                time.sleep(0.5)
                st.rerun()

# ====================
# TAB 2: 复盘模式 (不变)
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
