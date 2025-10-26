from fastapi import FastAPI, HTTPException
from schemas import EmailRequest
from email_utils import send_email

app = FastAPI(title="FastAPI Email Integration")

@app.post("/send-email/")
async def send_email_endpoint(email: EmailRequest):
    """API endpoint to send an email"""
    result = send_email(email.to, email.subject, email.body)
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result
