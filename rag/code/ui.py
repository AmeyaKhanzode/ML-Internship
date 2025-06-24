import streamlit as st
import importnb
import io
import os
import shutil
import chromadb

with importnb.Notebook():
    import rag

# --- Elegant Modern UI Styling ---
st.markdown(
    """
    <style>
    body {
        background: #181c24;
        color: #e0e6ed !important;
        font-family: 'Inter', 'Segoe UI', 'Roboto', sans-serif;
    }
    .stApp {
        background: #181c24;
        min-height: 100vh;
    }
    .stTextInput > div > div > input {
        background: #232936;
        color: #e0e6ed;
        border: 1.5px solid #4f8cff;
        font-size: 1.1em;
        border-radius: 8px;
        padding: 0.5em 1em;
        transition: border 0.2s;
    }
    .stTextInput > div > div > input:focus {
        border: 1.5px solid #7ed957;
        outline: none;
    }
    .stButton > button {
        background: linear-gradient(90deg, #4f8cff, #7ed957);
        color: #fff;
        border: none;
        font-size: 1.05em;
        font-weight: 600;
        border-radius: 8px;
        padding: 0.5em 1.5em;
        margin-top: 0.5em;
        box-shadow: 0 2px 8px rgba(79,140,255,0.08);
        transition: background 0.2s, box-shadow 0.2s;
    }
    .stButton > button:hover {
        background: linear-gradient(90deg, #7ed957, #4f8cff);
        box-shadow: 0 4px 16px rgba(126,217,87,0.12);
    }
    .stFileUploader {
        background: #232936;
        border: 1.5px solid #4f8cff;
        border-radius: 10px;
        padding: 1em;
        color: #e0e6ed;
    }
    .stSpinner > div > div {
        color: #4f8cff !important;
        font-size: 1.1em;
    }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #4f8cff;
        font-family: 'Inter', 'Segoe UI', 'Roboto', sans-serif;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    .stMarkdown p {
        color: #e0e6ed;
        font-size: 1.08em;
    }
    </style>
    <link href="https://fonts.googleapis.com/css?family=Inter:400,700&display=swap" rel="stylesheet">
    """,
    unsafe_allow_html=True
)

st.markdown("""
# 📄 Document Q&A
Welcome! Upload your files and ask questions about your documents in style.
""", unsafe_allow_html=True)

uploaded_files = st.file_uploader("Upload your files here", accept_multiple_files=True)

def reset_db():
    try:
        client = chromadb.PersistentClient(path="my_db")
        for col in client.list_collections():
            client.delete_collection(name=col.name)
    except Exception as e:
        st.warning(f"Failed to clear Chroma DB: {e}")

if uploaded_files:
    new_files = [f for f in uploaded_files if f.name not in st.session_state.get("seen", set())]
    if new_files:
        with st.spinner("Processing uploaded files..."):
            reset_db()
            st.session_state.vectordb, st.session_state.retriever = rag.init_db()
            st.session_state.qa_chain = rag.create_qa_chain(st.session_state.retriever)
            st.session_state.seen = set()
            for file in uploaded_files:
                chunks = rag.pipeline(st.session_state.vectordb, file)
                st.session_state.seen.add(file.name)

    query = st.text_input("Enter your question")
    if query:
        with st.spinner("Answering your query..."):
            st.markdown(f"<div style='background:#232936;border:1.5px solid #4f8cff;padding:1em;border-radius:10px;box-shadow:0 0 10px #4f8cff22;'>💡 <b>Answer:</b><br>{rag.handle_query(query, st.session_state.qa_chain, None)['result']}</div>", unsafe_allow_html=True)