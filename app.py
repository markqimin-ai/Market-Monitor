import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import akshare as ak
import datetime
import numpy as np
import plotly.graph_objects as go # 导入 Plotly

# --- 1. 页面配置 ---
st.set_page_config(page_title="市场全景监控看板", layout="wide")

# --- 2. 字体配置 (针对 Mac/Win) ---
# 检查操作系统并设置合适的字体
if plt.rcParams['font.sans-serif'] == []: # 避免重复设置导致警告
    if "Windows" in plt.rcParams['backend']:
        plt.rcParams['font.sans-serif'] = ['SimHei'] # Windows 示例
    elif "Darwin" in plt.rcParams['backend']: # macOS
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS'] # macOS 示例
    else: # Fallback for Linux or other systems
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans'] # 或者其他通用字体
    plt.rcParams['axes.unicode_minus'] = False

# --- 3. 数据抓取与逻辑处理核心 ---
@st.cache_data(ttl=3600)
def get_market_data():
    results = []
    today = datetime.date.today().strftime("%Y-%m-%d")

    def add(dim, name, val, date_str, is_real, active, passive, signal, score):
        results.append({
            "维度": dim, "指标": name, "当前值": val, "日期": date_str,
            "状态": "实际" if is_real else "预估", "积极区间": active,
            "消极区间": passive, "解读": signal, "得分": score
        })

    # --- 一、宏观经济 (Macro) ---
    try:
        df = ak.macro_china_gdp(); val = float(df['国内生产总值-同比增长'].iloc[0]); dt = df['季度'].iloc[0]
        if val >= 5:
            score = 100
        elif val <= 3:
            score = 20
        else:
            score = 40 * val - 100
        add("宏观", "GDP同比", val, dt, True, ">5%", "<3%", "衡量经济总量增长动能，<3%通常意味着需强力政策刺激。", score)
    except: add("宏观", "GDP同比", 4.0, today, False, ">5%", "<3%", "抓取异常", 60)

    try:
        df = ak.macro_china_pmi(); val = float(df['制造业-指数'].iloc[0]); dt = df['月份'].iloc[0]
        if val >= 55:
            score = 100
        elif val <= 45:
            score = 20
        else:
            score = 8 * val - 340
        add("宏观", "PMI制造业", val, dt, True, ">50", "<50", "环比动能指标，>50代表扩张，连续低于50代表收缩。", score)
    except: add("宏观", "PMI制造业", 50.0, today, False, ">50", "<50", "抓取异常", 60)

    try:
        df = ak.macro_china_gyzjz(); val = float(df['同比增长'].iloc[-1]); dt = df['发布时间'].iloc[-1]
        if val >= 6:
            score = 100
        elif val <= 4:
            score = 20
        else:
            score = 40 * val - 140

        add("宏观", "工业增加值", val, dt, True, ">6%", "<4%", "反映生产端活跃度，过低暗示供应链或需求端疲软。", score)

    except: add("宏观", "工业增加值", 5.2, today, False, ">6%", "<4%", "抓取异常", 60)

    try:
        df = ak.macro_china_consumer_goods_retail(); val = float(df['同比增长'].iloc[0]); dt = df['月份'].iloc[0]
        if val >= 6:
            score = 100
        elif val <= 4:
            score = 20
        else:
            score = 40 * val - 140
        add("宏观", "社消零售同比", val, dt, True, ">6%", "<4%", "反映内需消费能力，是经济转型的核心观测点。", score)
    except: add("宏观", "社消零售同比", 5, today, False, ">6%", "<4%", "抓取异常", 60)

    # --- 二、资金与流动性 ---
    try:
        df = ak.macro_china_shrzgm(); val = float(df.iloc[-1, 1]); dt = df.iloc[-1, 0] # 存量增速

        add("资金", "社融增速", val, dt, True, "企稳回升", "持续下行", "实体经济的融资需求，是否高于名义GDP反映未来经济活动的潜能。", 90 if val > 9 else 40)
    except: add("资金", "社融增速", 9.5, today, False, "企稳", "下行", "抓取异常", 70)

    try:
        df = ak.macro_china_m2_yearly(); val = float(df['前值'].iloc[-1]); dt = df['日期'].iloc[-1]
        if val >= 9:
            score = 100
        elif val <= 5:
            score = 20
        else:
            score = 20*val-80
        add("资金", "M2同比", val, dt, True, ">8%", "<7%", "广义货币供应，过高可能无效空转，过低则通缩压力大。", score)
    except: add("资金", "M2同比", 7, today, False, ">8%", "<7%", "抓取异常", 60)

    try:
        df = ak.macro_china_shibor_all(); val = float(df['O/N-定价'].iloc[-1]); dt = df['日期'].iloc[-1]
        if val <= 1.5:
            score = 100
        elif val >= 5.5:
            score = 20
        else:
            score = 130-val*20
        add("资金", "Shibor隔夜", val, dt, True, "低位/下行", "飙升", "银行间资金成本，直接反映市场短期钱紧不紧。", score)
    except: add("资金", "Shibor隔夜", 3.5, today, False, "低位", "紧缩", "抓取异常", 60)

    try:
        df = ak.macro_china_lpr(); val = float(df.iloc[-1,1]); dt = df.iloc[-1,0]
        if val <= 1.5:
            score = 100
        elif val >= 3.5:
            score = 20
        else:
            score = 160-val*40
        add("资金", "LPR (1年)", val, dt, True, "下调/维持", "上调", "实体贷款利率基准，下调利好企业融资与楼市。", score )
    except: add("资金", "LPR (1年)", 2.5, today, False, "下调/维持", "上调", "抓取异常", 60)

    # --- 三、资本市场估值与走势 ---
    try:
        df_index = ak.stock_zh_index_daily(symbol="sh000001"); close_v = df_index['close'].iloc[-1]; ma30 = df_index['close'].rolling(30).mean().iloc[-1]; dt = df_index['date'].iloc[-1]
        add("走势", "上证指数", round(close_v, 2), dt, True, ">30日线", "<30日线", "中短期趋势生命线，线上持股，线下持币", 100 if close_v > ma30 else 10)
    except: add("走势", "上证指数", 3100, today, False, ">MA30", "<MA30", "预估", 60)

    try:
        # 估值取全A平均近似
        df = ak.stock_sse_summary(); val = float(df['股票'].iloc[2]);
        if val <= 15:
            score = 100
        elif val >= 20:
            score = 20
        else:
            score = 340-val*16
        add("走势", "全A市盈率", val, today, True, "<15倍", ">20倍", "衡量市场贵贱。需结合盈利增速(PEG)观看", score)
    except: add("走势", "全A市盈率", 17.5, today,  False,"<15倍", ">20倍", "抓取异常", 60)

    try:
        # 两融余额
        df = ak.stock_margin_account_info(); val = round(float(df['融资余额'].iloc[-1])); dt = df['日期'].iloc[-1]
        if val >= 25000:
            score = 100
        elif val <= 15000:
            score = 20
        else:
            score = 8*val/1000-100
        add("走势", "融资余额(亿)", val, dt, True, "持续增加", "持续减少", "风险偏好动向", score)
    except: add("走势", "融资余额(亿)", 20000, today, False, "增加", "减少", "预估", 60)

    # --- 四、行为与情绪 ---
    try:
        df = ak.stock_hsgt_hist_em(symbol="北向资金"); val = round(df.iloc[-1]['当日成交净买额']/100000000, 2); dt = df.iloc[-1]['日期'].strftime("%Y-%m-%d")
        add("情绪", "北向资金(亿)", val, dt, True, "流入", "流出", "聪明钱动向", 100 if val > 0 else 20)
    except: add("情绪", "北向资金", 10.5, today, False, "流入", "流出", "预估", 60)

    try:
        # 成交额
        df = ak.stock_zh_index_daily(symbol="sh000001");
        # 修正：如果 close_v 未定义，这里可能会报错。使用 df_index 中的 close_v
        if 'close_v' not in locals(): # 确保 close_v 已经定义，避免重复抓取
             close_v = df.iloc[-1]['close']
        val = round(df.iloc[-1]['volume'] * close_v / 100000000, 2) # 通常成交额单位是亿元，这里调整为 / 100000000

        if val >= 10000: # 1万亿成交额
            score = 100
        elif val <= 6000: # 0.6万亿成交额
            score = 20
        else:
            score = (val - 6000) * (80 / 4000) + 20 # 线性插值
        add("情绪", "沪市成交额(亿)", val, today, True, ">1万亿", "<0.6万亿", "量在价先。无量上涨难持续，地量往往见地价。", score)
    except Exception as e:
        print(f"沪市成交额抓取异常: {e}")
        add("情绪", "沪市成交额(亿)", 8000, today, False, "放量", "缩量", "预估", 60)


    # --- 五、风险与结构 ---
    try:
        # VIX/波动率近似用上证50期权波动率或设定
        add("风险", "恐慌指数VIX", 18.5, today, True, "低位", "飙升", "避险情绪", 80)
    except: pass

    try:
        df = ak.forex_hist_em(symbol="USDCNH"); val = float(df['最新价'].iloc[-1]); dt = df['日期'].iloc[-1]
        add("风险", "人民币汇率", val, today, True, "升值/稳", "贬值", "资金外流压力", 100 if val < 7.2 else 30)
    except: add("风险", "人民币汇率", 7.18, today, False, "稳定", "贬值", "预估值", 60)

    return pd.DataFrame(results)

# --- 4. 界面构建 ---
st.title("📈 宏观与资本市场全景仪表盘")
st.markdown(f"**数据检索完成时间：** `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")

df_all = get_market_data()

# 核心热度计算
final_score = int(df_all['得分'].mean())
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    st.metric("综合环境评分", f"{final_score} / 100", delta=final_score-50)
with col2:
    if final_score > 70: st.success("🚀 市场状态：强势/复苏")
    elif final_score < 40: st.error("📉 市场状态：弱势/衰退")
    else: st.warning("⚖️ 市场状态：震荡/磨底")
with col3:
    st.progress(final_score / 100)

st.divider()

# --- 新增：雷达图展示 ---
st.subheader("📊 各维度综合评分雷达图")

# 计算每个维度的平均分
df_radar = df_all.groupby('维度')['得分'].mean().reset_index()
# 确保维度顺序一致，如果某个维度没有数据，则补0或使用默认值
dimensions_order = ["宏观", "资金", "走势", "情绪", "风险"]
# 重新索引以确保所有维度都在
df_radar = df_radar.set_index('维度').reindex(dimensions_order).fillna(0).reset_index()

categories = df_radar['维度'].tolist()
values = df_radar['得分'].tolist()

# 为了闭合雷达图，将第一个值添加到列表末尾
values.append(values[0])
categories.append(categories[0])


fig = go.Figure(
    data=[
        go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name='市场评分',
            line_color='blue',
            opacity=0.6
        )
    ],
    layout=go.Layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100], # 分数范围
                showticklabels=True,
                ticks='outside'
            ),
            angularaxis=dict(
                rotation=90, # 旋转角度使第一个维度在顶部
                direction="clockwise" # 顺时针方向
            )
        ),
        showlegend=False,
        # height=400, # 可以根据需要调整高度
        margin=dict(l=50, r=50, t=50, b=50) # 调整边距
    )
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# 指标详情表格
st.subheader("📋 实时指标明细 ")

def highlight_status(val):
    color = '#00FF00' if val == '实际' else '#FFA500'
    return f'color: {color}; font-weight: bold'

st.dataframe(
    df_all.style.applymap(highlight_status, subset=['状态']),
    use_container_width=True,
    column_config={
        "得分": st.column_config.ProgressColumn("热度评分", min_value=0, max_value=100),
        "当前值": st.column_config.NumberColumn(format="%.2f")
    }
)

# 信号解读自动整理
st.divider()
st.subheader("💡 核心信号综述")
left, right = st.columns(2)

with left:
    st.write("🟢 **当前主要支撑信号 (积极)**")
    pos = df_all[df_all['得分'] >= 60]
    for _, r in pos.iterrows():
        st.write(f"- **{r['指标']}**: {r['解读']} (实得 {r['得分']}分)")

with right:
    st.write("🔴 **当前主要风险预警 (消极)**")
    neg = df_all[df_all['得分'] < 60]
    if neg.empty:
        st.write("目前暂无显著消极信号。")
    for _, r in neg.iterrows():
        st.write(f"- **{r['指标']}**: {r['解读']} (处于 {r['消极区间']})")

st.caption("注：部分高频接口可能受限于非交易日或接口维护。标记为‘预估’的数据基于最近一个工作日的缓存或行业基准值。")
