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
    
# --- 3. 侧边栏：设定今日目标 (新增功能！) ---
with st.sidebar:
    st.header("🎯 今日目标")
    daily_goal = st.number_input("销售额目标 ($)", value=2000, step=100)

# --- 4. 主界面：输入表单 (手机优化版) ---

# 1. 顶部：进度条激励
df = load_data()
if not df.empty:
    # 处理数据格式，确保 Amount 是数字
    if 'Amount' in df.columns:
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    total_sales = df['Amount'].sum()
else:
    total_sales = 0

# 计算进度
progress = min(total_sales / daily_goal, 1.0) # 最大 100%
st.metric("今日业绩", f"${total_sales:,.0f}", f"目标: ${daily_goal}")
st.progress(progress)

st.divider()

# 2. 极速录入表单
with st.form("entry_form", clear_on_submit=True):
    st.caption("🚀 快速录入")
    
    # 第一行：谁来了？(使用列布局节省空间)
    c1, c2, c3 = st.columns([1.5, 1, 1])
    with c1:
        age = st.selectbox("年龄", ["20s", "30s", "40s", "50+", "Teens"], index=1)
    with c2:
        gender = st.selectbox("性别", ["女", "男", "组合"], index=0)
    with c3:
        race = st.selectbox("种族", ["Asian", "White", "Black", "Latino", "Other"], index=0)

    # 第二行：意图
    intent = st.radio("进店意图", 
                      ["闲逛 (Browsing)", "明确目标 (Specific)", "取货/礼物 (Pickup/Gift)"], 
                      horizontal=True)

    st.write("") # 空行间距
    
    # 第三行：结果 (核心交互！)
    # ⚠️ 这里的 radio 如果选中"买了"，我们希望能弹窗输入金额
    # 但在 Form 里无法做动态交互，所以我们用简单的逻辑：
    outcome = st.radio("最终结果", ["✅ 买了 (Bought)", "❌ 没买 (No Buy)"], horizontal=True)

    st.divider()
    
    # 第四行：根据情况填空
    # 为了手机不拥挤，我们将金额和原因并列，提示用户只填一项
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        amount = st.number_input("💰 金额 (成交填这里)", min_value=0.0, step=10.0)
    with col_input2:
        no_buy_reason = st.selectbox("🤔 原因 (没买选这里)", 
                                     ["N/A", "Just looking", "Price", "Competitor", "Out of Stock"])

    # 提交大按钮
    submitted = st.form_submit_button("🔥 提交记录", use_container_width=True)

    if submitted:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 智能逻辑：如果是“没买”，强制把金额设为 0
        final_amount = amount if "Bought" in outcome else 0
        final_reason = no_buy_reason if "No Buy" in outcome else ""

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
        st.toast(f"已保存！目前总业绩: ${total_sales + final_amount:,.0f}")
        
        # 延迟刷新，让进度条动起来
        import time
        time.sleep(1)
        st.rerun()

# --- 5. 历史记录 (折叠起来，不占地) ---
st.write("")
with st.expander("📊 点击查看今日详细列表"):
    if not df.empty:
        # 把最新的显示在最前面
        st.dataframe(df.iloc[::-1], use_container_width=True)
    else:
        st.info("暂无数据")

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