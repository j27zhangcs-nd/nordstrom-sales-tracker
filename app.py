import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- 1. 页面配置 ---
st.set_page_config(page_title="柜台销售记录", page_icon="💄")

# 标题区域
st.title("💄 柜台销售记录器")
st.caption("Nordstrom 柜台 - 快速交互记录")

# --- 2. 数据处理函数 ---
FILE_NAME = f"sales_log_{datetime.now().strftime('%Y')}.csv"

def save_data(data):
    """追加写入 CSV"""
    df_new = pd.DataFrame([data])
    if not os.path.isfile(FILE_NAME):
        df_new.to_csv(FILE_NAME, index=False)
    else:
        df_new.to_csv(FILE_NAME, mode='a', header=False, index=False)

def load_data():
    """读取数据用于显示"""
    if os.path.isfile(FILE_NAME):
        return pd.read_csv(FILE_NAME)
    return pd.DataFrame()

# --- 3. 输入表单 (适配手机操作) ---
with st.form("entry_form", clear_on_submit=True):
    # --- 顾客画像 ---
    st.subheader("1. 顾客画像 (Profile)")
    
    col1, col2 = st.columns(2)
    with col1:
        age = st.selectbox("年龄段", ["20s", "30s", "40s", "50+", "Teens"], index=1)
        gender = st.radio("性别", ["女", "男", "组合"], horizontal=True)
    with col2:
        race = st.selectbox("种族估测", ["Asian", "White", "Black", "Latino", "Other"], index=0)

    st.divider()

    # --- 意图与结果 ---
    st.subheader("2. 交互详情 (Interaction)")
    
    intent = st.radio(
        "进店意图 (Intent)",
        ["Browsing (闲逛)", "Specific (明确目标)", "Gift (买礼物)", "Intercepted (拦截)"],
    )

    st.write("") # 空一行增加间距
    outcome = st.radio("最终结果 (Outcome)", ["Bought (买了)", "No Buy (没买)"], horizontal=True)

    st.divider()
    
    # --- 补充信息 ---
    st.info("👇 选填一项 (根据结果)")
    amount = st.number_input("金额 (如果买了)", min_value=0.0, step=10.0)
    no_buy_reason = st.selectbox("原因 (如果没买)", 
                                 ["N/A", "Just looking", "Price", "Competitor", "Out of Stock"])

    # 提交按钮 - 设为全宽，方便手机点击
    submitted = st.form_submit_button("✅ 提交记录", use_container_width=True)

    if submitted:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        final_amount = amount if outcome == "Bought (买了)" else 0
        final_reason = no_buy_reason if outcome == "No Buy (没买)" else ""

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
        save_data(new_entry)
        st.toast("已保存！加油开下一单！") # 手机上会弹出一个小提示

# --- 4. 实时数据反馈 ---
st.divider()
st.subheader("📊 今日战报")

df = load_data()
if not df.empty:
    # 简单的今日统计
    total_sales = df['Amount'].sum()
    count = len(df)
    conversion = (len(df[df['Outcome']=="Bought (买了)"]) / count) * 100

    c1, c2, c3 = st.columns(3)
    c1.metric("总销售额", f"${total_sales:,.0f}")
    c2.metric("客流量", f"{count}")
    c3.metric("转化率", f"{conversion:.0f}%")
else:
    st.caption("暂无数据，等待第一位顾客...")