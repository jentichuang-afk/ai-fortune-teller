import streamlit as st
from google import genai
from google.genai import types
from streamlit_mic_recorder import mic_recorder
import speech_recognition as sr
import io
from pydub import AudioSegment

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

# --- 初始化對話與狀態記憶 (Session State) ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "fortune_result" not in st.session_state:
    st.session_state.fortune_result = None
if "show_voice_chat" not in st.session_state:
    st.session_state.show_voice_chat = False

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
    background-color: rgba(20, 10, 40, 0.8) !important;
    border: 1px solid rgba(255, 215, 0, 0.5) !important;
    color: #ffffff !important;
    box-shadow: 0 4px 6px rgba(0,0,0,0.5) !important;
}

/* 確保選擇框內部文字顏色為白色 */
div[data-baseweb="select"] span {
    color: #ffffff !important;
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

import datetime
import urllib.parse
from streamlit_javascript import st_javascript

# --- 獲取客戶端 (瀏覽器) 所在時區的當下時間 ---
# 這樣可以確保無論伺服器在哪個時區，AI 收到的都是使用者當地的日期與時間
client_date_js = "new Date().toLocaleDateString('zh-TW', { year: 'numeric', month: '2-digit', day: '2-digit' })"
client_local_date = st_javascript(client_date_js)

# 如果還抓不到 (初次載入或JS未執行)，先用伺服器時間備用
if not client_local_date:
    today_str = datetime.date.today().strftime("%Y年%m月%d日")
    current_year = datetime.date.today().year
else:
    # client_local_date 格式為 "YYYY/MM/DD" (根據 zh-TW)
    parts = client_local_date.split("/")
    if len(parts) == 3:
        today_str = f"{parts[0]}年{parts[1]}月{parts[2]}日"
        current_year = parts[0]
    else:
        today_str = datetime.date.today().strftime("%Y年%m月%d日")
        current_year = datetime.date.today().year

# --- 從網址參數 (URL Query Params) 讀取個人資料 ---
query_params = st.query_params

default_name = query_params.get("n", "")
default_gender = query_params.get("g", "男")
gender_options = ["男", "女", "其他", "保密"]
default_gender_idx = gender_options.index(default_gender) if default_gender in gender_options else 0

# 預設時間處理
default_date = datetime.date(1990, 1, 1)
if "d" in query_params:
    try:
        default_date = datetime.datetime.strptime(query_params.get("d"), "%Y-%m-%d").date()
    except ValueError:
        pass

default_time = datetime.time(12, 0)
if "t" in query_params:
    try:
        default_time = datetime.datetime.strptime(query_params.get("t"), "%H:%M").time()
    except ValueError:
        pass

# 根據 URL 是否有帶參數來顯示歡迎語
if default_name:
    st.success(f"🌟 歡迎回來！已從專屬連結載入 **{default_name}** 的命理設定檔。")

with st.form("fortune_form"):
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("您的姓名", value=default_name, placeholder="請輸入姓名")
    with col2:
        gender = st.selectbox("性別", gender_options, index=default_gender_idx)
    
    min_date = datetime.date(1920, 1, 1)
    max_date = datetime.date.today()
    
    col3, col4 = st.columns(2)
    with col3:
        birth_date = st.date_input("出生日期", min_value=min_date, max_value=max_date, value=default_date)
    with col4:
        birth_time = st.time_input("出生時間", value=default_time)
        
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
        
    col_form_btn1, col_form_btn2 = st.columns(2)
    with col_form_btn1:
        submitted = st.form_submit_button("✨ 祈求四柱神諭 ✨")
    with col_form_btn2:
        daily_fortune_btn = st.form_submit_button("🌞 今日運勢分析 (含化解建議)")

# --- 產生個人專屬連結 (無痕儲存) ---
st.write("---")
st.markdown("### 🔗 儲存個人資料 (專屬連結)")
st.info("為了保護您的隱私，我們不將個人資料儲存在雲端伺服器。按下方按鈕即可產生「**包含個人資料的專屬網址**」，只要將該網址加入書籤 (我的最愛)，下次點開就會自動填好所有資料哦！")

if st.button("🔗 產生專屬個人連結"):
    if name.strip():
        # 將表單狀態編碼到 URL 參數
        params = {
            "n": name.strip(),
            "g": gender,
            "d": birth_date.strftime("%Y-%m-%d"),
            "t": birth_time.strftime("%H:%M")
        }
        
        # 獲取當前 Host URL 以生成完整連結字串
        # 在 Streamlit 中產生相對應 URL 可以透過組合
        query_string = urllib.parse.urlencode(params)
        st.success("✅ **專屬連結已產生！請複製下方網址並加到瀏覽器書籤：**")
        
        # 嘗試使用 st.query_params 將參數推播至實體網址列 (Streamlit 1.30+)
        try:
            st.query_params.from_dict(params)
        except Exception as e:
            pass # 回退容錯
            
        st.code(f"?{query_string}", language="text")
        st.markdown("<p style='font-size:0.9em; color:#FFD700;'>☝️ 我們已將參數加進您上方的網址列，請直接按下 <b>Ctrl + D</b> 或點擊網址列旁邊的星星圖案，將該網址加入我的最愛即可！</p>", unsafe_allow_html=True)
    else:
        st.warning("⚠️ 請先在上方表單填寫姓名，才能產生專屬連結。")

# --- 處理送出：四柱神諭 ---
if submitted:
    if not name or not question:
        st.warning("請填寫您的姓名與想問的問題，神明才能給予指引。")
    elif not client:
        st.warning("系統尚未配置 API 金鑰，請聯絡管理員設定後再試。")
    else:
        # 重新祈求神諭時，清空之前的對話與記憶
        st.session_state.chat_history = []
        st.session_state.show_voice_chat = False
        st.session_state.fortune_result = None
        
        # 開始算命動畫
        with st.spinner("🌌 正在與星辰共鳴，解譯命運的軌跡..."):
            
            # 定義 Prompt 文本，要求回傳 JSON 格式
            prompt = f"""
            你現在是一位擁有數十年經驗的頂尖命理大師，精通「紫微斗數」、「八字命理」、「西方占星」與「塔羅牌」。
            今天是 {today_str}。在回答任何關於「今年」、「明年」或特定年份的運勢時，請務必以今年 ({current_year}年) 為基準進行推算，切勿給出過期年份的預測。
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
                from google.genai.errors import APIError
                
                models_to_try = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash']
                response = None
                used_model = None
                
                for model_name in models_to_try:
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                        )
                        used_model = model_name
                        break # 成功取得回應跳出迴圈
                    except APIError as e:
                        if "429" in str(e) or "Resource exhausted" in str(e):
                            continue # 限額錯誤，換下一個模型
                        else:
                            raise e # 其他錯誤直接拋出
                            
                if not response:
                    raise Exception("所有可用模型的 API 請求額度皆已耗盡，請稍後再試。")
                    
                # 提示使用者可能發生的降級
                if used_model != models_to_try[0]:
                    st.toast(f"ℹ️ 系統已自動切換至備援星象盤 ({used_model}) 為您推演。", icon="🔄")
                
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
                
                # 將算命結果存入 Session Context，供後續語音對話使用
                st.session_state.fortune_result = raw_text
                
            except json.JSONDecodeError:
                st.error("🔮 觀星台被雲霧遮蔽，解碼星象失敗，請稍後再重試一次。")
                st.write(response.text if response else "無回應") # 開發偵錯用
            except Exception as e:
                st.error(f"🔮 觀星台被雲霧遮蔽，預測失敗。原因：{str(e)}")

# --- 處理送出：今日運勢分析 ---
if daily_fortune_btn:
    if not name:
        st.warning("請填寫您的姓名，神明才能為您解析今日運勢。")
    elif not client:
        st.warning("系統尚未配置 API 金鑰，請聯絡管理員設定後再試。")
    else:
        # 重新祈求神諭時，清空之前的對話與記憶
        st.session_state.chat_history = []
        st.session_state.show_voice_chat = False
        st.session_state.fortune_result = None
        
        with st.spinner("🌞 正在結合星象與天氣，推算您今日的專屬運勢..."):
            prompt = f"""
            你現在是一位關心信眾、具備深厚命理學背景的大師，精通「紫微斗數」、「八字命理」、「西方占星」與「塔羅牌」。
            今天是 {today_str}。
            請根據以下使用者的資訊，綜合運用「紫微斗數」、「八字命理」、「西方占星」與「塔羅牌」這四種不同視角，來交叉推算他「今天 ({today_str}) 一整天的綜合運勢」。
            **強制要求：如果運勢中有任何不順遂、健康疑慮、或是可能發生衝突的「壞運勢」部分，你必須明確列出，並緊接著提供具體、可行、且能安定人心的「化解法則或開運建議」。**
            語氣要溫暖、像是一位長輩在叮嚀。
            
            **使用者資訊**：
            - 姓名：{name}
            - 性別：{gender}
            - 出生時間：{birth_date} {birth_time}
            
            請直接輸出一段充滿關懷的長文分析（請用 Markdown 格式，適當使用標題、粗體與條列式，將四種命理的觀點分段或融合解釋，並特別標註「化解重點」）。
            """
            
            try:
                from google.genai.errors import APIError
                models_to_try = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash']
                response = None
                
                for attempt_model in models_to_try:
                    try:
                        response = client.models.generate_content(
                            model=attempt_model,
                            contents=prompt,
                        )
                        if response and response.text:
                            # 將結果存入 session_state 供語音模組使用 (這樣語音模組也能針對今日運勢聊天)
                            st.session_state.fortune_result = response.text
                            st.markdown("<div class='result-card'><h3>🌞 今日運勢與化解指引</h3>" + response.text.replace('\n', '<br>') + "</div>", unsafe_allow_html=True)
                            break
                    except APIError as e:
                        if "429" in str(e) and attempt_model != models_to_try[-1]:
                            continue
                        raise e
                        
            except Exception as e:
                st.error(f"🌞 雲層太厚，看不清您的今日運勢。原因：{str(e)}")

# --- 語音諮詢服務模組 ---
if st.session_state.fortune_result:
    st.write("---")
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("💬 進一步語音討論", key="open_voice_chat", use_container_width=True):
            st.session_state.show_voice_chat = True
            
    if st.session_state.show_voice_chat:
        st.markdown("### 🎙️ 靈性語音對話")
        st.info("請按下下方麥克風按鈕開始說話，再次點擊結束錄音，大師會親自為您解答。")
        
        # 顯示歷史對話記錄
        for chat in st.session_state.chat_history:
            if chat["role"] == "user":
                with st.chat_message("user", avatar="👤"):
                    st.write(chat["content"])
            else:
                with st.chat_message("assistant", avatar="🔮"):
                    st.write(chat["content"])

        # 錄音組件
        audio_dict = mic_recorder(
            start_prompt="🔴 按此開始錄音",
            stop_prompt="⏹️ 按此停止並送出",
            just_once=True,
            use_container_width=True,
            key='mic_recorder'
        )
        
        if audio_dict:
            with st.spinner("🎧 大師正在聆聽您的心聲..."):
                # 將語音轉換為文字 (使用 SpeechRecognition 與 Google Web Speech API)
                r = sr.Recognizer()
                try:
                    # 將瀏覽器傳來的 WebM/Ogg 原始音檔轉為 pydub AudioSegment
                    audio_data_io = io.BytesIO(audio_dict['bytes'])
                    audio_segment = AudioSegment.from_file(audio_data_io)
                    
                    # 將 AudioSegment 匯出為標準的 PCM WAV 格式放入記憶體
                    wav_io = io.BytesIO()
                    audio_segment.export(wav_io, format="wav")
                    wav_io.seek(0)
                    
                    # 讓 SpeechRecognition 讀取標準的 WAV
                    with sr.AudioFile(wav_io) as source:
                        audio = r.record(source)
                    # 辨識中文
                    user_text = r.recognize_google(audio, language='zh-TW')
                    
                    if user_text:
                        # 加入歷史紀錄並立刻顯示在畫面上
                        st.session_state.chat_history.append({"role": "user", "content": user_text})
                        with st.chat_message("user", avatar="👤"):
                            st.write(user_text)
                            
                        # 向 Gemini 請求對話
                        with st.chat_message("assistant", avatar="🔮"):
                            with st.spinner("✨ 大師正在為您解惑..."):
                                # 組合 System Instruction (包含算命結果背景) 與歷史訊息
                                chat_prompt = f"""
                                你是那位溫暖且充滿神秘感的命理大師。
                                剛剛你為這位使用者算出的命理結果如下（請作為對話背景參考，不要重複貼上）：
                                {st.session_state.fortune_result}
                                
                                請針對他接下來的問題進行安撫、建議與解惑。語氣要口語、自然且溫馨。
                                使用者的問題是：{user_text}
                                """
                                
                                try:
                                    chat_response = client.models.generate_content(
                                        model='gemini-2.5-flash',
                                        contents=chat_prompt,
                                    )
                                    reply_text = chat_response.text
                                    st.write(reply_text)
                                    st.session_state.chat_history.append({"role": "assistant", "content": reply_text})
                                except Exception as e:
                                    st.error(f"對話中斷：{str(e)}")
                                
                except sr.UnknownValueError:
                    st.warning("聽不清楚您的聲音，請再說一次。")
                except sr.RequestError as e:
                    st.error(f"語音辨識服務發生錯誤：{e}")
                except Exception as e:
                    st.error(f"錄音處理錯誤：{str(e)}")
