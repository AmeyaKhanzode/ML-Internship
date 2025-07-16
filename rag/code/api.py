from fastapi import FastAPI, Request
import importnb

with importnb.Notebook():
    import rag
    import convo_db_utils

app = FastAPI()
vectordb, retriever = rag.init_db()
qa_chain = rag.create_qa_chain(retriever)


@app.post("/teams/webhook")
async def teams_webhook(req: Request):
    body = await req.json()
    user_text = body.get("text", "")
    user_id = body["from"]["id"]

    if not user_text.strip():
        return {"type": "message", "text": "Please ask a valid HR question."}

    try:
        result = rag.handle_query(user_text, qa_chain, user_id)
        response_text = result["result"]
    except Exception as e:
        response_text = f"⚠️ Error: {e}"
    
    import uuid
    from datetime import datetime

    response_id = str(uuid.uuid4())
    session_id = user_id  # You could generate if not using Teams user_id

    entry = {
        "query": user_text,
        "response": response_text,
        "response_id": response_id,
        "session_id": session_id,
    }

    try:
        convo_db_utils.add_entry(entry)
        print(f"[Teams] Entry added: {entry}")
    except Exception as e:
        print(f"[Teams] DB insert error: {e}")

    return {
        "type": "message",
        "text": response_text
    }