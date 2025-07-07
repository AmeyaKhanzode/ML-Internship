import streamlit as st
import importnb
import time
import hashlib
from datetime import datetime
import html

# Load your RAG logic
with importnb.Notebook():
    import rag

# --- Page config ---
st.set_page_config("📚 Smart Document Assistant", layout="wide")

# --- Helper function ---
def get_file_hash(file):
    return hashlib.md5(f"{file.name}_{file.size}".encode()).hexdigest()

# --- Initialize session state ---
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'vectordb' not in st.session_state:
    st.session_state.vectordb, st.session_state.retriever = rag.init_db()
    st.session_state.qa_chain = rag.create_qa_chain(st.session_state.retriever)
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = set()
if 'is_thinking' not in st.session_state:
    st.session_state.is_thinking = False

# --- Layout ---
st.title("📚 Smart Document Assistant")
col_chat, col_upload = st.columns([2, 1], gap="large")

# --- Chat Section ---
with col_chat:
    st.subheader("Conversation")

    # --- Chat Bubbles CSS ---
    chat_bubble_css = """
    <style>
    .chat-container {
        display: flex;
        flex-direction: column;
        gap: 10px;
        max-width: 100%;
    }
    .user-bubble, .bot-bubble {
        padding: 10px 15px;
        border-radius: 15px;
        max-width: 80%;
        white-space: pre-wrap;
        word-wrap: break-word;
    }
    .user-bubble {
        align-self: flex-end;
        background-color: #DCF8C6;
        color: black;
    }
    .bot-bubble {
        align-self: flex-start;
        background-color: #F1F0F0;
        color: black;
    }
    .timestamp {
        font-size: 0.75em;
        color: gray;
        margin-top: 2px;
    }
    </style>
    """
    st.markdown(chat_bubble_css, unsafe_allow_html=True)
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)

    # --- Display Messages as Bubbles ---
    for msg in st.session_state.chat_history:
        role = msg["role"]
        content = html.escape(msg["content"])
        timestamp = msg["timestamp"]
        bubble_class = "user-bubble" if role == "user" else "bot-bubble"
        st.markdown(
            f"""
            <div class="{bubble_class}">
                {content}
                <div class="timestamp">{timestamp}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    if st.session_state.is_thinking:
        st.markdown(
            """
            <div class="bot-bubble">
                🤖 <i>Thinking...</i>
            </div>
            """, unsafe_allow_html=True
        )

    st.markdown('</div>', unsafe_allow_html=True)

    # --- Chat Input Form ---
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_input("Ask something about your documents:")
        submitted = st.form_submit_button("Send")

    if submitted and user_input:
        now = datetime.now().strftime("%H:%M")
        st.session_state.chat_history.append({"role": "user", "content": user_input, "timestamp": now})
        st.session_state.is_thinking = True
        st.rerun()

    if st.session_state.is_thinking:
        user_msg = st.session_state.chat_history[-1]["content"]
        try:
            result = rag.handle_query(user_msg, st.session_state.qa_chain, None)['result']
        except Exception as e:
            result = f"⚠️ Error: {e}"
        now = datetime.now().strftime("%H:%M")
        st.session_state.chat_history.append({"role": "bot", "content": result, "timestamp": now})
        st.session_state.is_thinking = False
        st.rerun()

# --- File Upload Section ---
with col_upload:
    st.subheader("📁 Upload Documents")
    uploaded_files = st.file_uploader("Supported formats: PDF, TXT, DOCX", type=["pdf", "txt", "docx"], accept_multiple_files=True)

    if uploaded_files:
        new_files = [f for f in uploaded_files if get_file_hash(f) not in st.session_state.processed_files]
        if new_files:
            with st.spinner("Processing documents..."):
                for file in new_files:
                    try:
                        rag.pipeline(st.session_state.vectordb, file)
                        st.session_state.processed_files.add(get_file_hash(file))
                    except Exception as e:
                        st.error(f"❌ {file.name}: {e}")
                st.session_state.qa_chain = rag.create_qa_chain(st.session_state.retriever)
            st.success(f"✅ {len(new_files)} file(s) processed.")
        else:
            st.info("All uploaded documents are already processed.")