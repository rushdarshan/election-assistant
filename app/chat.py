from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import google.generativeai as genai
import os
from app.stats import record_ai_usage, record_topic

router = APIRouter()
templates = Jinja2Templates(directory="templates")

api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_CIVIC_API_KEY")
model = None
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash", system_instruction="""You are an election assistant. Answer questions based on official U.S. election procedures. Do not speculate or give partisan advice. Keep responses under 100 words. Refuse speculation. Use HTML formatting for your answers (e.g. <p>, <ul>, <li>).""")

@router.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    chat_history = request.session.get("chat_history", [])
    return templates.TemplateResponse(request=request, name="chat.html", context= {
        "request": request,
        "active_nav": "chat",
        "chat_history": chat_history
    })

@router.post("/chat", response_class=HTMLResponse)
async def chat_post(request: Request, message: str = Form(...)):
    chat_history = request.session.get("chat_history", [])
    
    user_msg = {"role": "user", "content": message[:500]}
    chat_history.append(user_msg)
    
    record_topic(message)
    
    if model:
        record_ai_usage("vertex_ai")
        try:
            # Build history for model
            history = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} for m in chat_history]
            chat = model.start_chat(history=history[:-1])
            response = chat.send_message(user_msg["content"])
            ai_msg = {"role": "assistant", "content": response.text}
        except Exception as e:
            print(f"Chat API Error: {e}")
            ai_msg = {"role": "assistant", "content": f"<p>I'm having trouble connecting right now. Error details: {e}</p>"}
    else:
        record_ai_usage("fallback")
        ai_msg = {"role": "assistant", "content": "<p>AI is not configured. This is a fallback response.</p>"}
        
    chat_history.append(ai_msg)
    
    if len(chat_history) > 20:
        chat_history = chat_history[-20:]
        
    request.session["chat_history"] = chat_history
    
    return templates.TemplateResponse(request=request, name="chat_messages.html", context= {
        "request": request,
        "messages": [user_msg, ai_msg]
    })
