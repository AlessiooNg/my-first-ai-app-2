import streamlit.components.v1 as components
import streamlit as st
from zhipuai import ZhipuAI
from supabase import create_client, Client
import uuid
import base64

st.set_page_config(page_title="包子", page_icon="🐱", layout="centered")

# ================= 🎙️ 升级版发声函数（支持高质量自然音色） =================
def speak_text(text):
    # 清理文本，防止JS注入错误
    clean_text = text.replace('\n', ' ').replace('"', '\\"').replace("'", "\\'")
    
    js = f"""
    <script>
    // 在语音库准备好之后再执行
    window.speechSynthesis.onvoiceschanged = function() {{
        var msg = new SpeechSynthesisUtterance("{clean_text}");
        var voices = window.speechSynthesis.getVoices();
        
        // 按优先级定义我们想要尝试的语音列表
        var preferredVoices = [
            "Microsoft Xiaoxiao", // 晓晓，Win/Edge 最自然的女声
            "Microsoft Xiaoyi",   // 晓伊，Win/Edge 年轻活泼
            "Tingting",           // 婷婷，macOS/iOS
            "Microsoft Yunxi"     // 云希，Win/Edge 自然男声
        ];
        
        var selectedVoice = null;
        for (var i = 0; i < preferredVoices.length; i++) {{
            for (var j = 0; j < voices.length; j++) {{
                if (voices[j].name.includes(preferredVoices[i])) {{
                    selectedVoice = voices[j];
                    break;
                }}
            }}
            if (selectedVoice) break;
        }}
        
        if (selectedVoice) {{
            msg.voice = selectedVoice;
        }}
        
        msg.lang = 'zh-CN';
        msg.rate = 1.0;
        msg.pitch = 1.1; // 稍微调低一点，听起来更自然
        window.speechSynthesis.speak(msg);
    }};
    </script>
    """
    components.html(js, height=0)

# ================= 🎨 注入 CSS 医美代码 =================
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp { background-color: #f5f7f9; }
    .stChatMessage { font-size: 16px; border-radius: 10px; padding: 10px; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e0e0e0; }
</style>
""", unsafe_allow_html=True)

# ================= 1. 连接云端数据库 =================
try:
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(supabase_url, supabase_key)
    zhipu_api_key = st.secrets["ZHIPU_KEY"]
except Exception as e:
    st.error(f"云端配置读取失败: {e}")
    st.stop()

# ================= 2. 识别用户并读取云端额度 =================
if "user_id" not in st.query_params:
    new_id = str(uuid.uuid4())
    st.query_params["user_id"] = new_id
    supabase.table("user_quotas").insert({"user_id": new_id, "quota": 3}).execute()
    user_quota = 3
else:
    user_id = st.query_params["user_id"]
    response = supabase.table("user_quotas").select("quota").eq("user_id", user_id).execute()
    if not response.data:
        supabase.table("user_quotas").insert({"user_id": user_id, "quota": 3}).execute()
        user_quota = 3
    else:
        user_quota = response.data[0]["quota"]

# ================= 侧边栏 =================
with st.sidebar:
    st.title("🐱 宠物档案")
    st.write("名字：包子")
    st.success("状态：已接入云端 + 视觉 + 声音")
    
    st.divider()
    st.write(f"当前云端剩余额度：**{user_quota}** 次")
    
    st.write("**给包子看张图：**")
    uploaded_file = st.file_uploader("支持 JPG / PNG", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        st.image(uploaded_file, caption="包子正在盯着这张图...", use_container_width=True)
    
    with st.expander("💳 额度用完了？点击解锁"):
        card_code = st.text_input("输入你的卡密：", type="password")
        if st.button("立即兑换"):
            valid_codes = st.secrets["VIP_CODES"]
            if card_code in valid_codes.values():
                new_quota = user_quota + 999
                supabase.table("user_quotas").update({"quota": new_quota}).eq("user_id", user_id).execute()
                st.success("兑换成功！刷新页面即可看到新额度！")
                st.rerun()
            else:
                st.error("卡密无效！")
    
    st.divider()
    if st.button("🗑️ 清空聊天记忆", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": "（包子甩了甩脑袋）我们重新认识一下吧！"}]
        st.rerun()
    
    system_prompt = st.text_area("设置 AI 角色（性格）：", value="你是一只可爱的、性格傲娇的电子宠物。你现在长眼睛了，能看到主人发给你的图片。", height=100)
    
    # ================= 留言反馈系统 =================
    st.divider()
    st.write("📬 给作者留言反馈：")
    user_feedback = st.text_area("你觉得包子好玩吗？哪里需要改进？")
    if st.button("提交反馈", use_container_width=True):
        if user_feedback:
            try:
                supabase.table("feedbacks").insert({"content": user_feedback}).execute()
                st.success("感谢你的反馈！已收到！")
            except Exception as e:
                st.error(f"提交失败: {e}")
        else:
            st.warning("写点什么再提交哦~")

    # ================= 👑 管理员通道 =================
    st.divider()
    if "is_admin" not in st.session_state:
        st.session_state.is_admin = False

    if not st.session_state.is_admin:
        admin_pwd = st.text_input("管理员通道密码：", type="password")
        if st.button("登录后台"):
            if admin_pwd == "boss888":
                st.session_state.is_admin = True
                st.rerun()
            else:
                st.error("密码错误！")
    else:
        st.success("欢迎回来，老板！")
        if st.button("退出后台"):
            st.session_state.is_admin = False
            st.rerun()

# ================= 网页主体 =================
if st.session_state.is_admin:
    st.title("👑 老板专属后台")
    st.subheader("用户反馈墙")
    try:
        res = supabase.table("feedbacks").select("*").order("created_at", desc=True).execute()
        if res.data:
            for item in res.data:
                st.info(f"🗣️ 用户留言：{item['content']}  \n⏰ 时间：{item['created_at'][:19]}")
        else:
            st.write("暂时还没有用户留言哦~")
    except Exception as e:
        st.error(f"数据拉取失败: {e}")
    st.stop()

# 💬 正常聊天视图
st.title("🐱 包子")
st.divider()

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "主人你好！我现在不仅能陪你聊天，还能看懂你发的图片，而且我还会说话啦！"}]

for msg in st.session_state.messages:
    if msg["role"] == "assistant":
        avatar_url = "https://api.dicebear.com/7.x/bottts/svg?seed=Baozi"
    else:
        avatar_url = None 
    with st.chat_message(msg["role"], avatar=avatar_url):
        st.write(msg["content"])

# ================= 核心商业逻辑拦截（暂时关闭） =================
# if user_quota <= 0:
#     st.warning("⚠️ 云端免费额度已耗尽。请查看左侧边栏，输入卡密解锁！")
#     st.chat_input("余额不足...", disabled=True)
# else:
# ================= 核心逻辑（暂时关闭拦截） =================
if prompt := st.chat_input("和你的宠物说点什么吧..."):
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant", avatar="https://api.dicebear.com/7.x/bottts/svg?seed=Baozi"):
        with st.spinner("包子正在看图思考中..."):
            try:
                client = ZhipuAI(api_key=zhipu_api_key)
                
                if uploaded_file is not None:
                    model_name = "glm-4v-flash"
                    uploaded_file.seek(0)
                    image_base64 = base64.b64encode(uploaded_file.read()).decode('utf-8')
                    messages_for_api = [
                        {"role": "system", "content": system_prompt},
                        *st.session_state.messages[:-1],
                        {"role": "user", "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                            {"type": "text", "text": prompt}
                        ]}
                    ]
                else:
                    model_name = "glm-4-flash"
                    messages_for_api = [{"role": "system", "content": system_prompt}] + st.session_state.messages

                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages_for_api,
                    stream=True
                )
                
                def generate_chunks():
                    for chunk in response:
                        if chunk.choices[0].delta.content is not None:
                            yield chunk.choices[0].delta.content
                
                ai_reply = st.write_stream(generate_chunks())
                st.session_state.messages.append({"role": "assistant", "content": ai_reply})
                
                # 🎙️ 触发语音朗读
                speak_text(ai_reply)
                
                # 注意：我们保留了扣费代码，这样数据库依然会记录你们聊了多少次
                new_quota = user_quota - 1
                supabase.table("user_quotas").update({"quota": new_quota}).eq("user_id", user_id).execute()
                
            except Exception as e:
                st.error(f"报错信息：{e}")
