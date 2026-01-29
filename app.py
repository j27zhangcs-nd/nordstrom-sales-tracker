import json
import os
import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. 页面配置 ---
st.set_page_config(page_title="柜台销售记录", page_icon="💄")

st.title("💄 柜台销售记录器 💄")
st.caption("Nordstrom 柜台 - 快速交互记录 (云端同步版)")

# --- 2. Google Sheets 连接配置 (新增部分) ---
# 使用 st.cache_resource 确保只连接一次，不用每次刷新都重连
@st.cache_resource
def get_google_sheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # 🕵️‍♀️ 双模侦测：判断是在本地还是云端
    if os.path.exists("secrets.json"):
        # 模式一：本地文件模式
        creds = ServiceAccountCredentials.from_json_keyfile_name("secrets.json", scope)
    else:
        # 模式二：云端 Secrets 模式 (从 st.secrets 获取字典)
        # 这里的 "gcp_service_account" 是我们等会儿要在云端设置的名字
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

    client = gspread.authorize(creds)
    
    # 记得改成你测试成功的那个表格名字，或者 ID
    sheet = client.open("Nordstrom Sales Data").sheet1 
    # 或者用 ID: client.open_by_key("你的ID").sheet1
    
    return sheet

# --- 数据处理函数 (重构部分) ---

def save_data(data):
    """将数据追加写入 Google Sheet"""
    sheet = get_google_sheet()
    
    # ⚠️ 关键：将字典 data 转换成列表 list，顺序必须和 Google Sheet 表头一致
    row = [
        data["Time"],
        data["Age"],
        data["Gender"],
        data["Race"],
        data["Intent"],
        data["Outcome"],
        data["Amount"],
        data["Reason"]
    ]
    sheet.append_row(row)

def load_data():
    """从 Google Sheet 读取数据用于显示"""
    try:
        sheet = get_google_sheet()
        # 获取所有记录
        records = sheet.get_all_records()
        # 转换成 DataFrame
        return pd.DataFrame(records)
    except Exception:
        # 如果读取失败或为空，返回空表
        return pd.DataFrame()

# --- 3. 输入表单 (UI 保持不变) ---
with st.form("entry_form", clear_on_submit=True):
    # --- 顾客画像 ---
    st.subheader("1. 顾客画像 (Profile)")
    
    col1, col2 = st.columns(2)
    with col1:
        age = st.selectbox("年龄段", ["20s", "30s", "40s", "50+", "Teens"], index=1)
        gender = st.radio("性别", ["女性", "男性", "组合"], horizontal=True)
    with col2:
        race = st.selectbox("种族估测", ["Asian", "White", "Black", "Latino", "Other"], index=0)

    st.divider()

    # --- 意图与结果 ---
    st.subheader("2. 交互详情 (Interaction)")
    
    intent = st.radio(
        "进店意图 (Intent)",
        ["Browsing (闲逛)", "Specific (明确目标)", "Gift (买礼物)", "Intercepted (拦截)"],
    )

    st.write("") 
    outcome = st.radio("最终结果 (Outcome)", ["Bought (买了)", "No Buy (没买)"], horizontal=True)

    st.divider()
    
    # --- 补充信息 ---
    st.info("👇 选填一项 (根据结果)")
    amount = st.number_input("金额 (如果买了)", min_value=0.0, step=10.0)
    no_buy_reason = st.selectbox("原因 (如果没买)", 
                                 ["N/A", "Just looking", "Price", "Competitor", "Out of Stock"])

    # 提交按钮
    submitted = st.form_submit_button("✅ 提交记录", use_container_width=True)

    if submitted:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        final_amount = amount if outcome == "Bought (买了)" else 0
        final_reason = no_buy_reason if outcome == "No Buy (没买)" else ""

        # 构造数据字典
        new_entry = {
            "Time": current_time,
            "Age": age,
            "Gender": gender,
            "Race": race,
            "Intent": intent,
            "Outcome": outcome,
            "Amount": final_amount,
            "Reason": final_reason
        }
        
        # 调用新的保存函数
        save_data(new_entry)
        
        st.toast("已保存到云端！加油开下一单！")
        
        # ⏳ 延迟一点点再刷新，让 Toast 提示能显示出来
        import time
        time.sleep(1)
        st.rerun()

# --- 4. 实时数据反馈 ---
st.divider()
st.subheader("📊 今日战报 (Google Sheets 同步中)")

df = load_data()
if not df.empty:
    # 简单的今日统计
    # 注意：从 Google Sheet 读回来的 Amount 可能是字符串，保险起见转一下类型
    if 'Amount' in df.columns:
        # 去掉可能的 $ 符号并转数字
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    
    total_sales = df['Amount'].sum()
    count = len(df)
    
    # 计算转化率 (防除零错误)
    if count > 0:
        conversion = (len(df[df['Outcome']=="Bought (买了)"]) / count) * 100
    else:
        conversion = 0

    c1, c2, c3 = st.columns(3)
    c1.metric("总销售额", f"${total_sales:,.0f}")
    c2.metric("客流量", f"{count}")
    c3.metric("转化率", f"{conversion:.0f}%")
else:
    st.caption("暂无数据，等待第一位顾客...")