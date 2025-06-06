
import streamlit as st
import importnb
import io
import os
import shutil
import chromadb

with importnb.Notebook():
    import rag

st.title("Ask about your documents!")
uploaded_files = st.file_uploader("Uploade your files here", accept_multiple_files=True)

def reset_db():
    try:
        client = chromadb.PersistentClient(path="my_db")
        for col in client.list_collections():
            client.delete_collection(name=col.name)
    except Exception as e:
        st.warning(f"Failed to clear Chroma DB: {e}")

# Only reset and re-init DB when files are uploaded
if uploaded_files:
    reset_db()
    st.session_state.vectordb, st.session_state.retriever = rag.init_db()
    st.session_state.qa_chain = rag.create_qa_chain(st.session_state.retriever)
    st.session_state.seen = set()
    for file in uploaded_files:
        rag.pipeline(st.session_state.vectordb, file)
        st.session_state.seen.add(file.name)

    query = st.text_input("Enter query here")
    if query:
        st.write(rag.handle_query(query, st.session_state.qa_chain, None)["result"])