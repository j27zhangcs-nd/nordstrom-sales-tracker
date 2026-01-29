import streamlit as st
import pandas as pd
import os
import json
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- 1. 页面配置 ---
st.set_page_config(page_title="柜台销售记录", page_icon="💄", layout="centered")

# 🔥🔥🔥 魔法 UI 样式区 (Magic CSS) 🔥🔥🔥
def add_custom_css():
    st.markdown("""
    <style>
    /* 1. 隐藏单选按钮原本的小圈圈 */
    div[role="radiogroup"] label > div:first-child {
        display: none !important;
    }
    
    /* 2. 把选项变成大大的方块按钮 */
    div[role="radiogroup"] label {
        background-color: #f0f2f6;
        padding: 15px 20px;
        border-radius: 10px;
        border: 2px solid transparent;
        margin-right: 10px;
        cursor: pointer;
        transition: all 0.2s;
        width: 100%;
        display: flex;
        justify-content: center;
        align-items: center;
        font-weight: bold;
    }

    /* 3. 鼠标悬停或者是选中时的效果 */
    div[role="radiogroup"] label:hover {
        background-color: #ffebeb;
        color: #ff4b4b;
        border: 2px solid #ff4b4b;
    }
    
    /* 4. Tab 标签页样式 */
    button[data-baseweb="tab"] {
        font-size: 18px !important;
        font-weight: bold !important;
        padding: 10px 20px !important;
    }
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
            last_item = all_values[-1]
            sheet.delete_rows(len(all_values))
            return True, last_item
        else:
            return False, None
    except Exception as e:
        return False, str(e)

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
    st.info("💡 提示：撤销和历史记录请去「📊 战绩复盘」标签页")

# --- 4. 主逻辑 ---

st.title("💄 Lancôme Sales Tracker")

# 准备数据
df = load_data()
if not df.empty:
    if 'Amount' in df.columns:
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    total_sales = df['Amount'].sum()
    count = len(df)
    # 获取所有“买了”的订单
    bought_df = df[df['Outcome'].str.contains("Bought", na=False)]
    
    if count > 0:
        conversion = (len(bought_df) / count) * 100
    else:
        conversion = 0
else:
    # ⚠️ 之前就是这里漏了定义 bought_df，现在补上了！
    total_sales = 0; count = 0; conversion = 0
    bought_df = pd.DataFrame() 

# Tab 分页
tab1, tab2 = st.tabs(["📝 快速录入", "📊 战绩复盘"])

# ====================
# TAB 1: 战斗模式
# ====================
with tab1:
    st.metric("今日业绩", f"${total_sales:,.0f}", f"目标: ${daily_goal} ({(total_sales/daily_goal)*100:.0f}%)")
    st.progress(min(total_sales / daily_goal, 1.0))
    
    st.divider()

    st.subheader("这一单的结果是？")
    outcome_mode = st.radio(
        "Outcome Mode", 
        ["✅ 买了 (Bought)", "❌ 没买 (No Buy)"], 
        horizontal=True, 
        label_visibility="collapsed"
    )

    with st.form("entry_form", clear_on_submit=True):
        st.caption("顾客画像 (点点点就行)")
        
        # 行 1: 年龄 (大按钮)
        age = st.radio("年龄", ["Teens", "20s", "30s", "40s", "50+"], horizontal=True)
        
        st.write("") 

        # 行 2: 性别 & 种族
        c1, c2 = st.columns(2)
        with c1: 
            gender = st.selectbox("性别", ["女", "男", "组合"])
        with c2: 
            race = st.selectbox("种族", ["Asian", "White", "Black", "Latino", "Other"])

        st.divider()
        st.caption("进店意图")
        intent = st.radio("意图", ["闲逛", "明确目标", "取货/礼物"], horizontal=True, label_visibility="collapsed")
        
        st.divider()

        # 动态逻辑
        if "Bought" in outcome_mode:
            st.success("✨ 开单大吉！")
            amount = st.number_input("成交金额 ($)", min_value=0.0, step=10.0)
            reason = ""
        else:
            st.warning("💪 下一位会更好！")
            amount = 0
            reason = st.selectbox("没买原因", ["Just looking", "Price", "Competitor", "Out of Stock", "Other"])

        st.write("")
        if st.form_submit_button("🚀 提交记录", use_container_width=True):
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_entry = {
                "Time": current_time, "Age": age, "Gender": gender, "Race": race,
                "Intent": intent, "Outcome": outcome_mode, "Amount": amount, "Reason": reason
            }
            save_data(new_entry)
            st.toast("✅ 已保存！")
            time.sleep(0.5)
            st.rerun()

# ====================
# TAB 2: 复盘模式
# ====================
with tab2:
    st.header("📊 今日数据看板")
    m1, m2, m3 = st.columns(3)
    m1.metric("总客流", f"{count}")
    m2.metric("转化率", f"{conversion:.0f}%")
    
    # 这里的计算现在安全了，因为 bought_df 肯定存在
    avg_order = (total_sales / len(bought_df)) if len(bought_df) > 0 else 0
    m3.metric("平均客单", f"${avg_order:.0f}")
    
    st.divider()

    if not df.empty:
        st.subheader("📈 销售趋势")
        chart_data = df.groupby("Intent")["Amount"].sum()
        st.bar_chart(chart_data)
    
    st.divider()
    
    st.subheader("📜 修正记录")
    col_undo, col_space = st.columns([1, 2])
    with col_undo:
        if st.button("↩️ 撤销上一单", type="primary"):
            with st.spinner("撤销中..."):
                success, info = delete_last_entry()
            if success:
                st.toast(f"✅ 已删除: ${info[6]}")
                time.sleep(1)
                st.rerun()
            else:
                st.error("无法撤销")
                
    if not df.empty:
        st.dataframe(df.iloc[::-1], use_container_width=True)