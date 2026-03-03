import streamlit as st
from google import genai
from google.genai import types

# --- 頁面設定 ---
st.set_page_config(
    page_title="星塵卜算 | 神秘 AI 算命",
    page_icon="🔮",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# --- 讀取 API 金鑰 ---
# 提供本地開發與 Streamlit Cloud 上線後的雙重支援
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except (KeyError, FileNotFoundError):
    API_KEY = None

# --- 初始化 Gemini 客戶端 ---
if API_KEY and API_KEY != "PLEASE_REPLACE_WITH_YOUR_ACTUAL_API_KEY":
    client = genai.Client(api_key=API_KEY)
else:
    client = None

# --- 自訂 CSS 樣式 ---
st.markdown("""
<style>
/* 隱藏預設選單與頁尾 */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* 整體背景與文字顏色 */
.stApp {
    background: radial-gradient(circle at center, #1b0a3a 0%, #050117 100%);
    color: #e0d5f5;
    font-family: 'Noto Serif TC', serif, sans-serif;
}

/* 標題與重點文字的發光效果 */
h1, h2, h3, .stMarkdown p {
    color: #ffd700;
    text-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
    text-align: center;
}

/* 輸入框與選擇框質感的玻璃擬物化 (Glassmorphism) */
.stTextInput > div > div > input,
.stSelectbox > div > div > div,
.stTextArea > div > div > textarea,
.stDateInput > div > div > input,
.stTimeInput > div > div > input {
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 215, 0, 0.3);
    color: white;
    box-shadow: 0 4px 6px rgba(0,0,0,0.3);
}

/* 按鈕美化 */
.stButton > button {
    background: linear-gradient(45deg, #4b0082, #191970);
    color: white;
    border: 1px solid #ffd700;
    border-radius: 20px;
    padding: 10px 24px;
    transition: all 0.3s ease;
    box-shadow: 0 0 15px rgba(255, 215, 0, 0.2);
    width: 100%;
}
.stButton > button:hover {
    background: linear-gradient(45deg, #191970, #4b0082);
    box-shadow: 0 0 25px rgba(255, 215, 0, 0.6);
    transform: scale(1.02);
}

/* 結果展示卡片 */
.result-card {
    background: rgba(25, 10, 50, 0.7);
    border: 1px solid #ffd700;
    border-radius: 15px;
    padding: 20px;
    margin-top: 20px;
    box-shadow: inset 0 0 20px rgba(0,0,0,0.5), 0 0 15px rgba(75, 0, 130, 0.5);
    color: #f0e6ff;
    line-height: 1.8;
}
.result-card h3 {
    border-bottom: 1px solid rgba(255,215,0,0.3);
    padding-bottom: 10px;
    margin-bottom: 15px;
}
</style>
""", unsafe_allow_html=True)

# --- 主程式介面 ---
st.markdown("<h1>🔮 星塵卜算 🔮</h1>", unsafe_allow_html=True)
st.markdown("<p style='font-size:1.1em; color:#bba0db;'>連結宇宙的智慧，洞悉你的過去與未來</p>", unsafe_allow_html=True)

st.write("---")

# 防呆提示
if not client:
    st.error("⚠️ 尚未設定有效的 API 金鑰。請於本地 `.streamlit/secrets.toml` 或 Streamlit Cloud 後台設定 `GEMINI_API_KEY`。")

with st.form("fortune_form"):
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("您的姓名", placeholder="請輸入姓名")
    with col2:
        gender = st.selectbox("性別", ["男", "女", "其他", "保密"])
    
    import datetime
    min_date = datetime.date(1920, 1, 1)
    max_date = datetime.date.today()
    default_date = datetime.date(1990, 1, 1)
    
    col3, col4 = st.columns(2)
    with col3:
        birth_date = st.date_input("出生日期", min_value=min_date, max_value=max_date, value=default_date)
    with col4:
        birth_time = st.time_input("出生時間")
        
    # 移除了單一算命方式選擇，改為一次算四種
    
    COMMON_QUESTIONS = [
        "自訂問題 (我要自己打)",
        "我接下來半年的事業運勢如何？",
        "我近期的感情狀況會有新發展嗎？",
        "我適合換工作或轉換跑道嗎？",
        "我最近的財運與投資吉凶如何？",
        "我的健康狀況有沒有需要特別留意的地方？",
        "我今年的人際關係與貴人運如何？"
    ]
    selected_q = st.selectbox("🔮 選擇想問的問題，或自行輸入", COMMON_QUESTIONS)
    
    if selected_q == "自訂問題 (我要自己打)":
        question = st.text_area("請誠心寫下您心中的疑問", placeholder="例如：我該如何突破目前的事業瓶頸？", height=80)
    else:
        question = selected_q
    
    submitted = st.form_submit_button("✨ 祈求神諭 ✨")

# --- 處理送出 ---
if submitted:
    if not name or not question:
        st.warning("請填寫您的姓名與想問的問題，神明才能給予指引。")
    elif not client:
        st.warning("系統尚未配置 API 金鑰，請聯絡管理員設定後再試。")
    else:
        # 開始算命動畫
        with st.spinner("🌌 正在與星辰共鳴，解譯命運的軌跡..."):
            
            # 定義 Prompt 文本，要求回傳 JSON 格式
            prompt = f"""
            你現在是一位擁有數十年經驗的頂尖命理大師，精通「紫微斗數」、「八字命理」、「西方占星」與「塔羅牌」。
            你的語氣應該充滿神秘感、溫暖且富有哲理。
            請根據以下使用者的資訊與問題，分別使用這四種不同的命理視角，為他進行深度的算命與解讀，請用繁體中文回答。
            請務必以 **純 JSON 格式** 輸出，不要包含任何 markdown 語法 (如 ```json) 或其他多餘的文字。
            JSON 的結構必須如下：
            {{
                "ziwei": "紫微斗數的完整解讀 (包含命盤簡析、解答、箴言，並使用適當的段落與折行排版)",
                "bazi": "八字命理的完整解讀",
                "astrology": "西方占星的完整解讀",
                "tarot": "塔羅牌陣的完整解讀"
            }}

            **使用者資訊**：
            - 姓名：{name}
            - 性別：{gender}
            - 出生時間：{birth_date} {birth_time}
            - 想問的問題：{question}
            """
            
            try:
                import json
                # 呼叫 Gemini 2.5 Flash API
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                )
                
                # 清理與解析 JSON 回應
                raw_text = response.text.strip()
                if raw_text.startswith("```json"):
                    raw_text = raw_text[7:-3].strip()
                elif raw_text.startswith("```"):
                    raw_text = raw_text[3:-3].strip()
                    
                result_data = json.loads(raw_text)
                
                # 美化呈現：使用 Tabs 一次展示四種結果
                st.markdown("<h3>📜 星辰匯聚的四大神諭 📜</h3>", unsafe_allow_html=True)
                tab1, tab2, tab3, tab4 = st.tabs(["☯️ 紫微斗數", "📜 八字命理", "✨ 西方占星", "🃏 塔羅牌陣"])
                
                with tab1:
                    st.markdown(f'<div class="result-card">{result_data.get("ziwei", "紫微斗數解讀失敗").replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
                with tab2:
                    st.markdown(f'<div class="result-card">{result_data.get("bazi", "八字命理解讀失敗").replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
                with tab3:
                    st.markdown(f'<div class="result-card">{result_data.get("astrology", "西方占星解讀失敗").replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
                with tab4:
                    st.markdown(f'<div class="result-card">{result_data.get("tarot", "塔羅牌解讀失敗").replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
                
            except json.JSONDecodeError:
                st.error("🔮 觀星台被雲霧遮蔽，解碼星象失敗，請稍後再重試一次。")
                st.write(response.text) # 開發偵錯用
            except Exception as e:
                st.error(f"🔮 觀星台被雲霧遮蔽，預測失敗。原因：{str(e)}")
