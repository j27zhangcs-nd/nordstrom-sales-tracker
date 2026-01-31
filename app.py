import streamlit as st
import pandas as pd
import os
import time
import gspread
import pytz
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- 1. 页面配置 ---
st.set_page_config(page_title="柜台销售记录", page_icon="💄", layout="centered")

# 🔥🔥🔥 魔法 UI 样式区 (保持不变) 🔥🔥🔥
def add_custom_css():
    st.markdown("""
    <style>
    html, body, [class*="css"] { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; }
    div[role="radiogroup"] label > div:first-child { display: none !important; }
    div[role="radiogroup"] label {
        background-color: #f8f9fa;
        padding: 10px 5px;
        border-radius: 6px;
        border: 1px solid #eee;
        margin: 0 !important;
        display: flex;
        justify-content: center;
        align-items: center;
        cursor: pointer;
        transition: all 0.2s ease;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        color: #666;
        font-weight: 500;
        font-size: 14px;
        height: 100%;
        width: 100%;
    }
    div[role="radiogroup"] { display: grid !important; gap: 8px !important; }
    div[role="radiogroup"][aria-label="Outcome Mode"] { grid-template-columns: 1fr 1fr !important; }
    div[role="radiogroup"][aria-label="年龄"] { grid-template-columns: repeat(5, 1fr) !important; }
    div[role="radiogroup"][aria-label="性别"] { grid-template-columns: repeat(3, 1fr) !important; }
    div[role="radiogroup"][aria-label="种族"] { grid-template-columns: repeat(5, 1fr) !important; }
    div[role="radiogroup"][aria-label="进店意图"] { grid-template-columns: repeat(3, 1fr) !important; }
    div[role="radiogroup"] label:has(input:checked) {
        background-color: #FFF0F5 !important;
        color: #9F1239 !important;
        border: 1px solid #FDA4AF !important;
        box-shadow: 0 2px 5px rgba(253, 164, 175, 0.4);
        font-weight: bold;
    }
    div[role="radiogroup"] label:hover { border-color: #FECDD3; color: #9F1239; }
    div[aria-label="Outcome Mode"] label { padding: 15px 10px !important; font-size: 16px !important; }
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

# --- 🕒 核心功能：获取西雅图时间 ---
def get_seattle_time():
    utc_now = datetime.now(pytz.utc)
    seattle_tz = pytz.timezone('America/Los_Angeles')
    return utc_now.astimezone(seattle_tz)

# --- 数据处理函数 ---
def save_data(data):
    sheet = get_google_sheet()
    row = [
        data["Time"], data["Age"], data["Gender"], data["Race"],
        data["Intent"], data["Outcome"], data["Amount"], data["Reason"]
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
    st.header("⚙️ 目标设置")
    daily_goal = st.number_input("🎯 今日目标 ($)", value=2000, step=100)
    
    seattle_now = get_seattle_time()
    st.caption(f"📍 西雅图时间: {seattle_now.strftime('%Y-%m-%d %H:%M')}")


# --- 4. 主逻辑 ---
st.title("💄 Jing's Nordstrom Beauty Sales Tracker")

# 1️⃣ 加载全部历史数据 (仓库)
df_all = load_data()

# 2️⃣ 准备“今天”的数据 (用于 Tab 1 录入)
today_str = seattle_now.strftime("%Y-%m-%d")

# 计算今日总销售额 (为了在 Tab 1 顶部显示)
total_sales_today = 0
if not df_all.empty and 'Time' in df_all.columns:
    df_today_only = df_all[df_all['Time'].astype(str).str.startswith(today_str)].copy()
    if not df_today_only.empty:
        df_today_only['Amount'] = pd.to_numeric(df_today_only['Amount'], errors='coerce').fillna(0)
        total_sales_today = df_today_only['Amount'].sum()

# Tab 分页
tab1, tab2 = st.tabs(["📝 快速录入 (Today)", "🗓️ 历史回看 (History)"])

# ====================
# TAB 1: 战斗模式 (永远只操作“今天”)
# ====================
with tab1:
    # 这里的进度条永远显示“今天”的
    st.metric("今日业绩", f"${total_sales_today:,.0f}", f"目标: ${daily_goal} ({(total_sales_today/daily_goal)*100:.0f}%)")
    st.progress(min(total_sales_today / daily_goal, 1.0))
    st.divider()

    outcome_mode = st.radio("Outcome Mode", ["✅ 买了 (Bought)", "❌ 没买 (No Buy)"], horizontal=True, label_visibility="collapsed")

    with st.form("entry_form", clear_on_submit=True):
        c_left, c_right = st.columns(2)
        with c_left:
            if "Bought" in outcome_mode:
                amount = st.number_input("成交金额 ($)", min_value=0.0, step=10.0)
            else:
                st.write("") 
                amount = 0 
        with c_right:
            if "No Buy" in outcome_mode:
                reason = st.selectbox("没买原因", ["Just looking", "Price", "Competitor", "Out of Stock", "Other"], label_visibility="collapsed")
            else:
                st.write("") 
                reason = "" 
        
        st.divider()
        st.caption("顾客画像")
        age = st.radio("年龄", ["年轻人", "中年人", "老年人"], horizontal=True)
        st.write("") 
        gender = st.radio("性别", ["女", "男"], horizontal=True)
        st.write("")
        race = st.radio("种族", ["白人", "华人", "其他亚裔", "其他美国人", "其他"], horizontal=True)
        st.divider()
        intent = st.radio("进店意图", ["闲逛", "明确目标", "取货/礼物"], horizontal=True)
        st.write("")
        st.write("")
        
        submit_label = "🚀 提交成交！" if "Bought" in outcome_mode else "📝 记录客流"
        
        if st.form_submit_button(submit_label, use_container_width=True):
            # 🔥 强制使用当前西雅图时间写入
            current_time_str = get_seattle_time().strftime("%Y-%m-%d %H:%M:%S")
            new_entry = {
                "Time": current_time_str, "Age": age, "Gender": gender, "Race": race,
                "Intent": intent, "Outcome": outcome_mode, "Amount": amount, "Reason": reason
            }
            save_data(new_entry)
            st.toast("✅ 已保存！")
            time.sleep(0.5)
            st.rerun()

# ====================
# TAB 2: 复盘模式 (穿越时空)
# ====================
with tab2:
    st.header("📊 数据看板")
    
    # 🔥🔥🔥 核心升级：日期选择器 🔥🔥🔥
    col_date, col_space = st.columns([2, 1])
    with col_date:
        # 默认值是西雅图的今天
        selected_date = st.date_input("📅 选择你要查看的日期", value=seattle_now.date())
    
    selected_date_str = selected_date.strftime("%Y-%m-%d")
    
    # 判断用户选的是不是“今天”
    is_viewing_today = (selected_date_str == today_str)

    # --- 数据筛选逻辑 ---
    df_view = pd.DataFrame()
    if not df_all.empty and 'Time' in df_all.columns:
        # 筛选出选定那天的数据
        df_view = df_all[df_all['Time'].astype(str).str.startswith(selected_date_str)].copy()
    
    # --- 计算指标 ---
    view_sales = 0
    view_count = 0
    view_conversion = 0
    view_bought_df = pd.DataFrame()

    if not df_view.empty:
        if 'Amount' in df_view.columns:
            df_view['Amount'] = pd.to_numeric(df_view['Amount'], errors='coerce').fillna(0)
        view_sales = df_view['Amount'].sum()
        view_count = len(df_view)
        view_bought_df = df_view[df_view['Outcome'].str.contains("Bought", na=False)]
        if view_count > 0:
            view_conversion = (len(view_bought_df) / view_count) * 100

    # --- 展示指标 ---
    st.caption(f"正在查看: {selected_date_str} 的数据")
    m1, m2, m3 = st.columns(3)
    m1.metric("总销售额", f"${view_sales:,.0f}")
    m2.metric("总客流", f"{view_count}")
    m3.metric("转化率", f"{view_conversion:.0f}%")
    
    st.divider()

    if not df_view.empty:
        st.subheader("📈 销售趋势")
        try:
            chart_data = df_view.groupby("Intent")["Amount"].sum()
            st.bar_chart(chart_data)
        except:
            st.caption("暂无图表数据")
        
        st.divider()
        
        # 🔥🔥🔥 安全机制 🔥🔥🔥
        # 只有在查看“今天”的数据时，才允许撤销/删除。
        # 查看历史数据时，我们隐藏这个按钮，防止你误删了上个月的记录。
        if is_viewing_today:
            st.subheader("📜 修正记录")
            col_undo, col_space2 = st.columns([1, 2])
            with col_undo:
                if st.button("↩️ 撤销上一单 (Undo Today)", type="primary"):
                    with st.spinner("撤销中..."):
                        success = delete_last_entry()
                    if success:
                        st.toast("✅ 已撤销")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("无法撤销")
        else:
            st.info("💡 历史数据仅供查看，不可撤销。")

        st.dataframe(df_view.iloc[::-1], use_container_width=True)
        
    else:
        st.info(f"📅 {selected_date_str} 没有销售记录。")