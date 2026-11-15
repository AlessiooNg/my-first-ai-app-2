import streamlit as st
from zhipuai import ZhipuAI
from supabase import create_client, Client
import uuid

# ================= 页面基础配置 =================
st.set_page_config(page_title="包子", page_icon="🐱", layout="centered")

# ================= 🎨 注入 CSS 医美代码 =================
st.markdown("""
<style>
    /* 隐藏 Streamlit 默认的顶栏菜单和底部水印 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* 修改整个网页的背景色为极其高级的浅灰色 */
    .stApp {
        background-color: #f5f7f9;
    }
    
    /* 让聊天框的字体变大、变好看 */
    .stChatMessage {
        font-size: 16px;
        border-radius: 10px;
        padding: 10px;
    }
    
    /* 给侧边栏加个背景色 */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e0e0e0;
    }
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
    st.success("状态：已接入云端数据库")
    
    st.divider()
    st.write(f"当前云端剩余额度：**{user_quota}** 次")
    
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
    
    system_prompt = st.text_area("设置 AI 角色（性格）：", value="你是一只可爱的、性格傲娇的电子宠物。", height=100)
    
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

# 👑 后台视图拦截
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
        
    st.stop() # 看完后台，停止运行下面的聊天逻辑


# 💬 正常聊天视图
st.title("🐱 包子")
st.divider()

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "主人你好！我已经接入了真实的大模型，现在我很聪明啦！"}]

# 渲染历史聊天记录（带酷炫头像）
for msg in st.session_state.messages:
    if msg["role"] == "assistant":
        avatar_url = "https://api.dicebear.com/7.x/bottts/svg?seed=Baozi"
    else:
        avatar_url = None 
    with st.chat_message(msg["role"], avatar=avatar_url):
        st.write(msg["content"])

# 核心商业逻辑拦截
if user_quota <= 0:
    st.warning("⚠️ 云端免费额度已耗尽。请查看左侧边栏，输入卡密解锁！")
    st.chat_input("余额不足...", disabled=True)
else:
    if prompt := st.chat_input("和你的宠物说点什么吧..."):
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant", avatar="https://api.dicebear.com/7.x/bottts/svg?seed=Baozi"):
            with st.spinner("包子思考中..."):
                try:
                    client = ZhipuAI(api_key=zhipu_api_key)
                    response = client.chat.completions.create(
                        model="glm-4-flash",
                        messages=[{"role": "system", "content": system_prompt}] + st.session_state.messages,
                        stream=True
                    )
                    
                    def generate_chunks():
                        for chunk in response:
                            if chunk.choices[0].delta.content is not None:
                                yield chunk.choices[0].delta.content
                    
                    ai_reply = st.write_stream(generate_chunks())
                    st.session_state.messages.append({"role": "assistant", "content": ai_reply})
                    
                    # 扣减云端额度
                    new_quota = user_quota - 1
                    supabase.table("user_quotas").update({"quota": new_quota}).eq("user_id", user_id).execute()
                    
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"报错信息：{e}")
