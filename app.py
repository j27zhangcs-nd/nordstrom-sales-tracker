import streamlit as st
import pandas as pd
import os
import json
import time  # 提到最前面，方便全局使用
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- 1. 页面配置 ---
st.set_page_config(page_title="柜台销售记录", page_icon="💄")

st.title("💄 柜台销售记录器")
st.caption("Nordstrom 柜台 - 快速交互记录 (云端同步版)")

# --- 2. Google Sheets 连接配置 ---
@st.cache_resource
def get_google_sheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # 🕵️‍♀️ 双模侦测：判断是在本地还是云端
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
    """追加写入"""
    sheet = get_google_sheet()
    row = [
        data["Time"], data["Age"], data["Gender"], data["Race"],
        data["Intent"], data["Outcome"], data["Amount"], data["Reason"]
    ]
    sheet.append_row(row)

def delete_last_entry():
    """💥 新增功能：撤销（删除）最后一行"""
    try:
        sheet = get_google_sheet()
        # 获取所有数据（为了知道有多少行）
        all_values = sheet.get_all_values()
        
        # 确保不仅仅只有表头（长度大于1才删）
        if len(all_values) > 1:
            last_item = all_values[-1] # 记录一下删了啥
            sheet.delete_rows(len(all_values)) # 删除最后一行
            return True, last_item
        else:
            return False, None
    except Exception as e:
        return False, str(e)

def load_data():
    """读取数据"""
    try:
        sheet = get_google_sheet()
        records = sheet.get_all_records()
        return pd.DataFrame(records)
    except Exception:
        return pd.DataFrame()

# --- 3. 侧边栏：设置与操作 (保持不变) ---
with st.sidebar:
    st.header("⚙️ 设置与操作")
    
    # 1. 目标设置
    daily_goal = st.number_input("🎯 今日目标 ($)", value=2000, step=100)
    
    st.divider()
    
    # 2. 撤销按钮
    st.warning("⚠️ 操作区")
    if st.button("↩️ 撤销上一单 (Undo)", type="primary"):
        with st.spinner("正在撤销..."): # 加个转圈圈动画
            success, info = delete_last_entry()
            
        if success:
            st.toast(f"✅ 已撤销上一笔: {info[5]} - ${info[6]}") # 提示删掉了什么
            time.sleep(1)
            st.rerun() # 强制刷新页面
        else:
            if info:
                st.error(f"撤销失败: {info}")
            else:
                st.info("表格是空的，没法撤销啦！")

# --- 4. 主界面：仪表盘 & 表单 ---

# 加载数据 (只加载一次，后面复用)
df = load_data()
if not df.empty:
    if 'Amount' in df.columns:
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    total_sales = df['Amount'].sum()
    count = len(df)
    # 计算转化率
    if count > 0:
        conversion = (len(df[df['Outcome'].str.contains("Bought", na=False)]) / count) * 100
    else:
        conversion = 0
else:
    total_sales = 0
    count = 0
    conversion = 0

# 1. 顶部：关键指标
c1, c2, c3 = st.columns(3)
c1.metric("今日业绩", f"${total_sales:,.0f}", f"目标: ${daily_goal}")
c2.metric("总客流", f"{count} 人")
c3.metric("转化率", f"{conversion:.0f}%")

# 进度条
progress = min(total_sales / daily_goal, 1.0)
st.progress(progress)

st.divider()

# --- 🔥 这里开始是本次优化的核心改动 🔥 ---

# 1. 这一单的结果是？(移出表单，变成全局开关)
# 这样点它的时候，下面的表单会立刻刷新
st.subheader("1. 这一单的结果是？")
outcome_mode = st.radio(
    "Outcome Mode", 
    ["✅ 买了 (Bought)", "❌ 没买 (No Buy)"], 
    horizontal=True, 
    label_visibility="collapsed" # 隐藏标题，更简洁
)

# 2. 极速录入表单
with st.form("entry_form", clear_on_submit=True):
    st.caption("2. 快速补充细节")
    
    # 第一行：顾客画像
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

    st.divider()
    
    # 第三行：根据“结果开关”条件显示 (Conditional Logic)
    
    if "Bought" in outcome_mode:
        # 如果是买了 -> 只显示金额
        st.info("💰 开单啦！")
        amount = st.number_input("输入金额 ($)", min_value=0.0, step=10.0)
        reason = "" # 自动把原因设为空
    else:
        # 如果没买 -> 只显示原因
        st.warning("🤔 没买...")
        amount = 0 # 自动把金额设为 0
        reason = st.selectbox("选择原因", ["Just looking", "Price", "Competitor", "Out of Stock", "Other"])

    # 提交按钮
    submitted = st.form_submit_button("🔥 提交记录", use_container_width=True)

    if submitted:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 构造数据 (直接使用上面逻辑里定义好的 amount 和 reason)
        new_entry = {
            "Time": current_time,
            "Age": age,
            "Gender": gender,
            "Race": race,
            "Intent": intent,
            "Outcome": outcome_mode, # 使用外面的开关状态
            "Amount": amount,
            "Reason": reason
        }
        
        save_data(new_entry)
        st.toast(f"已保存！")
        time.sleep(0.5)
        st.rerun()

# --- 5. 历史记录 (保持不变) ---
st.write("")
with st.expander("📊 点击查看今日详细列表"):
    if not df.empty:
        # iloc[::-1] 让最新的显示在第一行
        st.dataframe(df.iloc[::-1], use_container_width=True)
    else:
        st.info("暂无数据")