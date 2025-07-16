from fastapi import FastAPI, Request
from pydantic import BaseModel
import importnb

with importnb.Notebook():
    import rag
    import convo_db_utils

app = FastAPI()
vectordb, retriever = rag.init_db()
qa_chain = rag.create_qa_chain(retriever)

class QueryRequest(BaseModel):
    query: str
    user_id: str

class FeedbackRequest(BaseModel):
    response_id: str
    feedback: str  # "Good" or "Bad"
    reason: str = "None"

@app.post("/feedback")
async def submit_feedback(req: FeedbackRequest):
    convo_db_utils.update_feedback(req.response_id, req.feedback, req.reason)
    return {"status": "ok"}

@app.post("/query")
async def get_answer(req: QueryRequest):
    answer = rag.handle_query(req.query, qa_chain, None)
    return {"response": answer["result"]}