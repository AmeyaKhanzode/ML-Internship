import streamlit as st
import importnb
import time
import hashlib
from datetime import datetime
import html
import uuid

with importnb.Notebook():
    import rag
    import convo_db_utils
    import db_utils
print("="*198)
convo_db_utils.init_db()

st.set_page_config("HR Assistant", layout="wide")

def get_file_hash(file):
    return hashlib.md5(f"{file.name}_{file.size}".encode()).hexdigest()

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'vectordb' not in st.session_state:
    st.session_state.vectordb, st.session_state.retriever = rag.init_db()
    st.session_state.qa_chain = rag.create_qa_chain(st.session_state.retriever)
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = set()
if 'is_thinking' not in st.session_state:
    st.session_state.is_thinking = False
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if 'response_ids' not in st.session_state:
    st.session_state.response_ids = []
if 'just_added_entry' not in st.session_state:
    st.session_state.just_added_entry = False
if 'current_uploaded_files' not in st.session_state:
    st.session_state.current_uploaded_files = []

st.title("HR Assistant")
col_chat, col_upload = st.columns([2, 1], gap="large")

with col_chat:
    st.subheader("Conversation")

    chat_bubble_css = """
    <style>
    .chat-container {
        display: flex;
        flex-direction: column;
        gap: 20px;
        max-width: 100%;
    }
    .message-wrapper {
        display: flex;
        margin-bottom: 15px;
    }
    .message-wrapper.user {
        justify-content: flex-end;
    }
    .message-wrapper.bot {
        justify-content: flex-start;
    }
    .user-bubble, .bot-bubble {
        padding: 12px 16px;
        border-radius: 18px;
        max-width: 70%;
        white-space: pre-wrap;
        word-wrap: break-word;
        display: inline-block;
        width: auto;
        min-height: fit-content;
        line-height: 1.4;
    }
    .user-bubble {
        background-color: #DCF8C6;
        color: black;
        border-bottom-right-radius: 4px;
    }
    .bot-bubble {
        background-color: #F1F0F0;
        color: black;
        border-bottom-left-radius: 4px;
    }
    .timestamp {
        font-size: 0.75em;
        color: gray;
        margin-top: 4px;
        text-align: right;
    }
    .bot-bubble .timestamp {
        text-align: left;
    }
    .feedback-container {
        display: flex;
        gap: 10px;
        margin-top: 5px;
        margin-left: 10px;
    }
    .thumbs-up, .thumbs-down {
        background: none;
        border: 1px solid #ddd;
        border-radius: 50%;
        width: 35px;
        height: 35px;
        cursor: pointer;
        font-size: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s ease;
    }
    .thumbs-up:hover {
        background-color: #e8f5e8;
        border-color: #4CAF50;
    }
    .thumbs-down:hover {
        background-color: #ffebee;
        border-color: #f44336;
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
        
        wrapper_class = "user" if role == "user" else "bot"
        bubble_class = "user-bubble" if role == "user" else "bot-bubble"
        
        st.markdown(
            f"""
            <div class="message-wrapper {wrapper_class}">
                <div class="{bubble_class}">
                    {content}
                    <div class="timestamp">{timestamp}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Add feedback buttons only after bot messages
        if role == "bot":
            # Get the response_id from the message itself
            response_id = msg.get("response_id", "unknown")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("👍", key=f"thumbs_up_{response_id}"):
                    convo_db_utils.update_feedback(response_id, "up")
                    st.success("👍 Feedback recorded!")
            with col2:
                if st.button("👎", key=f"thumbs_down_{response_id}"):
                    convo_db_utils.update_feedback(response_id, "down")
                    st.success("👎 Feedback recorded :( Regenerating enhanced response.")
                    # Set is_thinking to True and rerun, so the thinking bubble is shown before generating enhanced response
                    st.session_state.is_thinking = "enhanced"
                    st.session_state.enhanced_context = {
                        "prev_user": st.session_state.chat_history[-2]["content"],
                        "prev_bot": st.session_state.chat_history[-1]["content"]
                    }
                    st.rerun()


    if st.session_state.is_thinking:
        st.markdown(
            """
            <div class="message-wrapper bot">
                <div class="bot-bubble">
                    🤖 <i>Thinking...</i>
                </div>
            </div>
            """, unsafe_allow_html=True
        )
        # If is_thinking is 'enhanced', generate enhanced response after showing thinking
        if st.session_state.is_thinking == "enhanced":
            prev_user = st.session_state.enhanced_context["prev_user"]
            prev_bot = st.session_state.enhanced_context["prev_bot"]
            try:
                enhanced_response = rag.generate_enhanced_response(prev_user, prev_bot, st.session_state.qa_chain)
            except Exception as e:
                enhanced_response = f"⚠️ Error: {e}"
            now = datetime.now().strftime("%H:%M")
            new_response_id = str(uuid.uuid4())
            st.session_state.chat_history.append({
                "response_id": new_response_id,
                "role": "bot",
                "content": f"✨ **Enhanced Response:**\n\n{enhanced_response}",
                "timestamp": now
            })
            st.session_state.response_ids.append(new_response_id)
            st.session_state.is_thinking = False
            st.session_state.enhanced_context = None
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    # --- Chat Input Form ---
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_input("Ask something about your documents:", disabled=st.session_state.is_thinking)
        submitted = st.form_submit_button("Send", disabled=st.session_state.is_thinking)
    if submitted and user_input:
        now = datetime.now().strftime("%H:%M")
        query_id = str(uuid.uuid4())
        st.session_state.chat_history.append({"query_id": query_id, "role": "user", "content": user_input, "timestamp": now})
        st.session_state.is_thinking = True
        st.rerun()
    if st.session_state.is_thinking:
        user_msg = st.session_state.chat_history[-1]["content"]
        try:
            result = rag.handle_query(user_msg, st.session_state.qa_chain, None)['result']
        except Exception as e:
            result = f"⚠️ Error: {e}"
        
        # Generate response_id here when creating the bot response
        response_id = str(uuid.uuid4())
        print(f"Generated new response_id: {response_id}")
        
        now = datetime.now().strftime("%H:%M")
        st.session_state.chat_history.append({
            "response_id": response_id, 
            "role": "bot", 
            "content": result, 
            "timestamp": now
        })
        st.session_state.response_ids.append(response_id)
        st.session_state.is_thinking = False
        st.session_state.just_added_entry = False
        st.rerun()
# --- File Upload Section ---
with col_upload:
    st.subheader("📁 Upload Documents")
    uploaded_files = st.file_uploader("Supported formats: PDF, TXT, DOCX", type=["pdf", "txt", "docx", "xlsx", "xlsb"], accept_multiple_files=True)
    
    # Track removed files
    if uploaded_files is not None:
        current_file_hashes = {get_file_hash(f) for f in uploaded_files}
        previous_file_hashes = {get_file_hash(f) for f in st.session_state.current_uploaded_files}
        
        removed_file_hashes = previous_file_hashes - current_file_hashes
        
        if removed_file_hashes:
            print(f"Files removed: {removed_file_hashes}")

            st.session_state.processed_files -= removed_file_hashes
            for removed_file_hash in removed_file_hashes:
                db_utils.mark_for_deletion(removed_file_hash)
                print(f"Removed file with hash {removed_file_hash} from vector db")

        st.session_state.current_uploaded_files = uploaded_files
    
    if uploaded_files:
        new_files = [f for f in uploaded_files if get_file_hash(f) not in st.session_state.processed_files]
        if new_files:
            with st.spinner("Processing documents..."):
                processed_count = 0
                for file in new_files:
                    try:
                        file.seek(0)
                        print("Entering pipeline")
                        result = rag.pipeline(st.session_state.vectordb, file)
                        print(f"Processing file: {file.name}, result: {result}")
                        if result:  # Only mark as processed if pipeline returns chunks
                            st.session_state.processed_files.add(get_file_hash(file))
                            processed_count += 1
                            st.write(f"✅ Processed: {file.name}")

                    except Exception as e:
                        st.error(f"❌ {file.name}: {str(e)}")
                        import traceback
                        st.error(f"Debug info: {traceback.format_exc()}")
                
                # Only recreate QA chain if we processed new files
                if processed_count > 0:
                    try:
                        st.session_state.qa_chain = rag.create_qa_chain(st.session_state.retriever)
                        st.success(f"✅ {processed_count} file(s) processed successfully.")
                    except Exception as e:
                        st.error(f"❌ Error updating QA chain: {str(e)}")
                else:
                    st.info("File(s) already processed.")
        else:
            st.info("All uploaded documents are already processed.")
    if st.session_state.chat_history != [] and st.session_state.just_added_entry == False:
        entry = {
            "query": st.session_state.chat_history[-2]["content"],
            "response": st.session_state.chat_history[-1]["content"],
            "response_id": st.session_state.response_ids[-1],
            "session_id": st.session_state.session_id
        }
        print(f"Entry: {entry}")
        print("="*200)
        convo_db_utils.add_entry(entry)
        st.session_state.just_added_entry = True
print("="*198)