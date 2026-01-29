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

# 🔥🔥🔥 魔法 UI 样式区 (V9: 全模块化 + 精准列数控制) 🔥🔥🔥
def add_custom_css():
    st.markdown("""
    <style>
    /* 全局字体 */
    html, body, [class*="css"] {
        font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    }

    /* 1. 隐藏单选按钮原本的小圆圈 */
    div[role="radiogroup"] label > div:first-child {
        display: none !important;
    }

    /* 2. 按钮基础样式 (通用卡片) */
    div[role="radiogroup"] label {
        background-color: #f8f9fa;
        padding: 10px 5px;        /* 减少内边距，为了让一排能塞下5个 */
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
        font-size: 14px;          /* 字体稍微改小一点点，防止挤 */
        height: 100%;
        width: 100%;
    }

    /* 3. 基础网格 (默认自动适应) */
    div[role="radiogroup"] {
        display: grid !important;
        gap: 8px !important;      /* 间距稍微调小，更紧凑 */
    }

    /* 🔥 4. 精准控制各模块列数 (CSS 魔法) 🔥 */
    
    /* 结果 (Outcome): 强制 2 列 */
    div[role="radiogroup"][aria-label="Outcome Mode"] {
        grid-template-columns: 1fr 1fr !important;
    }

    /* 年龄 (Age): 强制 5 列 (一排！) */
    div[role="radiogroup"][aria-label="年龄"] {
        grid-template-columns: repeat(5, 1fr) !important;
    }

    /* 性别 (Gender): 强制 3 列 (一排！) */
    div[role="radiogroup"][aria-label="性别"] {
        grid-template-columns: repeat(3, 1fr) !important;
    }

    /* 种族 (Race): 强制 5 列 (一排！) */
    /* 如果手机屏幕太窄，这行可能会挤，但为了“平行一排”的效果，我们强制设为5 */
    div[role="radiogroup"][aria-label="种族"] {
        grid-template-columns: repeat(5, 1fr) !important;
    }
    
    /* 意图 (Intent): 强制 3 列 */
    div[role="radiogroup"][aria-label="进店意图"] {
        grid-template-columns: repeat(3, 1fr) !important;
    }

    /* 5. 选中状态：晨曦粉 */
    div[role="radiogroup"] label:has(input:checked) {
        background-color: #FFF0F5 !important;
        color: #9F1239 !important;
        border: 1px solid #FDA4AF !important;
        box-shadow: 0 2px 5px rgba(253, 164, 175, 0.4);
        font-weight: bold;
    }
    
    div[role="radiogroup"] label:hover {
        border-color: #FECDD3;
        color: #9F1239;
    }

    /* 6. 特殊调整 */
    /* 让“结果”开关更高大上一点 */
    div[aria-label="Outcome Mode"] label {
        padding: 15px 10px !important;
        font-size: 16px !important;
    }
    
    /* 微调数字输入框的位置 */
    .stNumberInput, .stSelectbox {
        margin-top: -5px; 
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

st.title("💄 Jing's Nordstrom Beauty Sales Tracker")

# 准备数据
df = load_data()
if not df.empty:
    if 'Amount' in df.columns:
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    total_sales = df['Amount'].sum()
    count = len(df)
    bought_df = df[df['Outcome'].str.contains("Bought", na=False)]
    if count > 0:
        conversion = (len(bought_df) / count) * 100
    else:
        conversion = 0
else:
    total_sales = 0; count = 0; conversion = 0; bought_df = pd.DataFrame()

# Tab 分页
tab1, tab2 = st.tabs(["📝 快速录入", "📊 战绩复盘"])

# ====================
# TAB 1: 战斗模式
# ====================
with tab1:
    st.metric("今日业绩", f"${total_sales:,.0f}", f"目标: ${daily_goal} ({(total_sales/daily_goal)*100:.0f}%)")
    st.progress(min(total_sales / daily_goal, 1.0))
    st.divider()

    # 1. 第一步：结果总开关
    outcome_mode = st.radio(
        "Outcome Mode", 
        ["✅ 买了 (Bought)", "❌ 没买 (No Buy)"], 
        horizontal=True, 
        label_visibility="collapsed"
    )

    # 2. 第二步：表单区域
    with st.form("entry_form", clear_on_submit=True):
        
        # 平行模块布局：左金额，右原因
        c_left, c_right = st.columns(2)
        
        with c_left:
            if "Bought" in outcome_mode:
                amount = st.number_input("成交金额 ($)", min_value=0.0, step=10.0)
            else:
                st.write("") 
                amount = 0 

        with c_right:
            if "No Buy" in outcome_mode:
                # 原因这里也可以变成模块，但选项有点长，先保留 selectbox
                reason = st.selectbox("没买原因", ["Just looking", "Price", "Competitor", "Out of Stock", "Other"], label_visibility="collapsed")
            else:
                st.write("") 
                reason = "" 
        
        st.divider()
        
        # --- 全面模块化画像 (No More Dropdowns!) ---
        st.caption("顾客画像")
        
        # 年龄 (CSS 强制 5 列)
        age = st.radio("年龄", ["年轻人", "中年人", "老年人"], horizontal=True)
        st.write("") 

        # 性别 (CSS 强制 3 列) -> 以前是 selectbox，现在改成 radio 变模块
        gender = st.radio("性别", ["女", "男"], horizontal=True)
        st.write("")

        # 种族 (CSS 强制 5 列) -> 以前是 selectbox，现在改成 radio 变模块
        # 注意：因为这里有 5 个选项，CSS 会强制它们排一行，看起来非常整齐
        race = st.radio("种族", ["白人", "华人", "其他亚裔", "其他美国人", "其他"], horizontal=True)

        st.divider()

        # 意图 (CSS 强制 3 列)
        intent = st.radio("进店意图", ["闲逛", "明确目标", "取货/礼物"], horizontal=True)

        st.write("")
        st.write("")
        
        # 提交按钮
        submit_label = "🚀 提交成交！" if "Bought" in outcome_mode else "📝 记录客流"
        if st.form_submit_button(submit_label, use_container_width=True):
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
# TAB 2: 复盘模式 (保持不变)
# ====================
with tab2:
    st.header("📊 今日数据看板")
    m1, m2, m3 = st.columns(3)
    m1.metric("总客流", f"{count}")
    m2.metric("转化率", f"{conversion:.0f}%")
    avg_order = (total_sales / len(bought_df)) if len(bought_df) > 0 else 0
    m3.metric("平均客单", f"${avg_order:.0f}")
    
    st.divider()

    if not df.empty:
        st.subheader("📈 销售趋势")
        try:
            chart_data = df.groupby("Intent")["Amount"].sum()
            st.bar_chart(chart_data)
        except:
            st.caption("数据不足以生成图表")
    
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