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

st.set_page_config("HR Assistant", layout="wide", initial_sidebar_state="collapsed")

# Company logo and tagline
st.image("mobinext-logo-black.png", width=300)

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
    st.session_state.current_uploaded_files = set()
if 'show_feedback_reasons' not in st.session_state:
    st.session_state.show_feedback_reasons = {}
if 'selected_reasons' not in st.session_state:
    st.session_state.selected_reasons = {}
if 'bad_feedback_count' not in st.session_state:
    st.session_state.bad_feedback_count = {}

PAGES = {
    "HR Assistant": "main",
    "Admin": "admin"
}

if 'page' not in st.session_state:
    st.session_state.pages = list(PAGES.keys())

page = st.sidebar.selectbox("Select Page", list(PAGES.keys()))

# Handle hidden feedback analysis page
if 'current_page' in st.session_state and st.session_state.current_page == "Feedback Analysis":
    page = "Feedback Analysis"

if page == "HR Assistant":
    st.title("HR Assistant")
    st.markdown(
        "<p style='color: #888; font-size: 0.9em; margin-top: -10px;'>Powered by MobiNext Technologies Pvt. Ltd.</p>", 
        unsafe_allow_html=True
    )
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
            word-wrap: break-word;
            display: inline-block;
            width: auto;
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
                
                # Create unique key suffix based on message index to avoid duplicate keys
                msg_index = st.session_state.chat_history.index(msg)
                unique_key_suffix = f"{response_id}_{msg_index}"

                reasons = [
                    "Answer is incomplete.",
                    "Answer is irrelevant",
                    "Answer is completely wrong",
                    "No answer given"
                ]
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("👍", key=f"thumbs_up_{unique_key_suffix}"):
                        convo_db_utils.update_feedback(response_id, "up", "None")
                        st.success("👍 Feedback recorded!")
                        
                with col2:
                    if st.button("👎", key=f"thumbs_down_{unique_key_suffix}"):
                        print(f"Thumbs down clicked for response_id: {response_id}")
                        st.session_state.show_feedback_reasons[unique_key_suffix] = True
                        st.rerun()
                
                # Show feedback reason selection if thumbs down was clicked
                if st.session_state.show_feedback_reasons.get(unique_key_suffix, False):
                    st.write("**Please tell us why you gave a thumbs down:**")
                    selected_reason = st.radio(
                        "Select a reason:",
                        reasons,
                        key=f"reason_radio_{unique_key_suffix}"
                    )
                    
                    col_submit1, col_submit2 = st.columns(2)
                    with col_submit1:
                        if st.button("Submit Reason", key=f"submit_reason_{unique_key_suffix}"):
                            convo_db_utils.update_feedback(response_id, "down", selected_reason)
                            
                            # Increment bad feedback count for this response
                            st.session_state.bad_feedback_count[response_id] = st.session_state.bad_feedback_count.get(response_id, 0) + 1
                            
                            print(f"Bad feedback count for {response_id}: {st.session_state.bad_feedback_count[response_id]}")
                            
                            # Check if this is the second dislike for this response
                            if st.session_state.bad_feedback_count[response_id] >= 2:
                                now = datetime.now().strftime("%H:%M")
                                st.session_state.chat_history.append({
                                    "response_id": response_id,
                                    "role": "bot",
                                    "content": "Sorry for the back to back wrong feedbacks.\nFor accurate details kindly contact our HR. Name: Cristiano Ronaldo Contact Number: +91 2839173921 Email ID: ronaldothegoat@gmail.com",
                                    "timestamp": now
                                })
                                
                                st.session_state.show_feedback_reasons[unique_key_suffix] = False
                                st.rerun()
                            else:
                                st.success("Thank you for sharing your feedback! Regenerating new response.")
                                
                                # Clear the feedback reason display
                                st.session_state.show_feedback_reasons[unique_key_suffix] = False
                                
                                # Set is_thinking to True and rerun
                                result = convo_db_utils.get_thumbs_down_query(response_id)
                                if result is not None:
                                    prev_user, prev_bot, reason = result
                                    st.session_state.enhanced_context = {
                                        "prev_user": prev_user,
                                        "prev_bot": prev_bot,
                                        "reason": reason,
                                        "original_response_id": response_id
                                    }
                                    st.session_state.is_thinking = "enhanced"
                                    st.rerun()
                                else:
                                    st.error("Could not retrieve previous query and response for enhancement.")
                                    st.session_state.show_feedback_reasons[unique_key_suffix] = False
                    with col_submit2:
                        if st.button("Cancel", key=f"cancel_reason_{unique_key_suffix}"):
                            st.session_state.show_feedback_reasons[unique_key_suffix] = False
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
                bad_reason = st.session_state.enhanced_context["reason"]
                original_response_id = st.session_state.enhanced_context["original_response_id"]
                
                try:
                    enhanced_response = rag.generate_enhanced_response(prev_user, prev_bot, bad_reason, st.session_state.qa_chain)
                except Exception as e:
                    enhanced_response = f"⚠️ Error: {e}"
                
                now = datetime.now().strftime("%H:%M")
                st.session_state.chat_history.append({
                    "response_id": original_response_id,  # Use same response_id to track dislikes
                    "role": "bot",
                    "content": f"✨ **Enhanced Response:**\n\n{enhanced_response}",
                    "timestamp": now
                })
                st.session_state.is_thinking = False
                st.session_state.enhanced_context = None
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        # --- Chat Input Form ---
        with st.form("chat_form", clear_on_submit=True):
            user_input = st.text_input("Ask something about your documents:", disabled=st.session_state.is_thinking)
            submitted = st.form_submit_button("Send", disabled=st.session_state.is_thinking)
        
        # Set thinking state IMMEDIATELY when query is submitted
        if submitted and user_input:
            st.session_state.is_thinking = True
            now = datetime.now().strftime("%H:%M")
            query_id = str(uuid.uuid4())
            st.session_state.chat_history.append({"query_id": query_id, "role": "user", "content": user_input, "timestamp": now})
            st.rerun()
        
        # Process the query if we're thinking
        if st.session_state.is_thinking and st.session_state.is_thinking != "enhanced":
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
            st.session_state.just_added_entry = False  # Reset here, but it will be set to True below
            st.rerun()
    
    # --- File Upload Section ---
    with col_upload:
        st.subheader("📁 Upload Documents")
        uploaded_files = st.file_uploader("Supported formats: PDF, TXT, DOCX", type=["pdf", "txt", "docx", "xlsx", "xlsb"], accept_multiple_files=True)

        current_file_hashes = {db_utils.get_file_hash(f) for f in uploaded_files}
        st.session_state.current_uploaded_files.update(current_file_hashes)
        print(f"currently uploaded files in the session state are: {st.session_state.current_uploaded_files}")

        print(f"current_file_hashes: {current_file_hashes}")
        if current_file_hashes:
            removed_file_hashes = st.session_state.current_uploaded_files - current_file_hashes
            print(f"now removed file hashes are: {removed_file_hashes}")
           
            if removed_file_hashes:
                st.session_state.processed_files -= removed_file_hashes
                st.session_state.current_uploaded_files -= set(removed_file_hashes)
                for removed_file_hash in removed_file_hashes:
                    db_utils.mark_for_deletion(removed_file_hash)

        
        if uploaded_files:
            new_files = [f for f in uploaded_files if db_utils.get_file_hash(f) not in st.session_state.processed_files]
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
                                st.session_state.processed_files.add(db_utils.get_file_hash(file))
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
        
        # Database entry logic - runs after query processing
        if st.session_state.chat_history != [] and st.session_state.just_added_entry == False:
            # Only add entry if we have both user and bot messages
            if len(st.session_state.chat_history) >= 2:
                last_msg = st.session_state.chat_history[-1]
                second_last_msg = st.session_state.chat_history[-2]
                
                # Make sure we have a user query followed by a bot response
                if second_last_msg["role"] == "user" and last_msg["role"] == "bot":
                    entry = {
                        "query": second_last_msg["content"],
                        "response": last_msg["content"],
                        "response_id": st.session_state.response_ids[-1],
                        "session_id": st.session_state.session_id
                    }
                    print(f"Entry: {entry}")
                    print("="*200)
                    convo_db_utils.add_entry(entry)
                    st.session_state.just_added_entry = True
    
    print("="*198)

if page == "Admin":
    st.title("⚙️ Admin Dashboard")
    
    # Password protection
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False
    
    if not st.session_state.admin_authenticated:
        st.subheader("🔐 Admin Access")
        password = st.text_input("Enter admin password:", type="password")
        
        if st.button("Login"):
            # Set your admin password here
            ADMIN_PASSWORD = "mobinext"  # Change this to your desired password
            
            if password == ADMIN_PASSWORD:
                st.session_state.admin_authenticated = True
                st.success("✅ Access granted!")
                st.rerun()
            else:
                st.error("❌ Invalid password")
    else:
        # Admin dashboard content goes here
        st.success("🔓 Admin access granted")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Database Stats")
            try:
                processed_files_count = len(st.session_state.processed_files)
                st.metric("Processed Files", processed_files_count)
                
                conversation_count = len(st.session_state.chat_history)
                st.metric("Current Session Messages", conversation_count)
            except Exception as e:
                st.error(f"Error getting stats: {e}")
        
        with col2:
            st.subheader("🗑️ Database Management")
            
            if st.button("🗑️ Clear Vector Database"):
                try:
                    rag.flush_db()
                    st.session_state.processed_files = set()
                    st.session_state.vectordb, st.session_state.retriever = rag.init_db()
                    st.session_state.qa_chain = rag.create_qa_chain(st.session_state.retriever)
                    st.success("✅ Vector database cleared!")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
            
            st.subheader("Feedback Analysis")
            if st.button("Analyze Feedback"):
                st.session_state.current_page = "Feedback Analysis"
                st.rerun()
            
            if st.button("💬 Clear Chat History"):
                st.session_state.chat_history = []
                st.session_state.response_ids = []
                st.success("✅ Chat history cleared!")
        
        # Logout button
        if st.button("🚪 Logout"):
            st.session_state.admin_authenticated = False
            st.rerun()

elif page == "Feedback Analysis":
    st.title("📊 Feedback Analysis")

    if st.button("← Back to Admin"):
        if 'current_page' in st.session_state:
            del st.session_state.current_page
        st.rerun()

    bad_qrs = convo_db_utils.get_bad_query_response()

    for i, entry in enumerate(bad_qrs):
        st.markdown(f"""
            <div class='bad-qr'>
                <h3>Query: {bad_qrs[i]["query"]}</h3>
                <p>Reason: {bad_qrs[i]["reason"]}</p>
                <div class='response-text'>{bad_qrs[i]["response"]}</div>
            </div>
        """, unsafe_allow_html=True)

    # Custom CSS for bad query-response pairs
    st.markdown(
        """
        <style>
        .bad-qr {
            background-color: #ffebee !important;
            border: 2px solid #f44336 !important;
            border-radius: 10px !important;
            padding: 20px !important;
            margin: 15px 0 !important;
            box-shadow: 0 4px 8px rgba(244, 67, 54, 0.2) !important;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif !important;
        }

        .bad-qr h3 {
            color: #d32f2f !important;
            margin-top: 0 !important;
            margin-bottom: 10px !important;
            font-size: 1.2em !important;
            font-weight: 600 !important;
        }

        .response-text, .response-text *, .bad-qr p, .bad-qr span, .bad-qr div {
            color: #212121 !important;  /* Dark gray for visibility */
            background-color: transparent !important;
        }

        /* Override Streamlit styles just in case */
        .stMarkdown .bad-qr {
            background-color: #ffebee !important;
            border: 2px solid #f44336 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )