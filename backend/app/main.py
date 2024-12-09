import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
from typing import Optional, Dict
import json
from app.database import Database
from app.utils import process_audio_file, cleanup_temp_file
from app.prompts import load_prompts, get_prompt_content

load_dotenv()

app = FastAPI(title="Summary API")
db = Database()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SummaryRequest(BaseModel):
    text: str
    prompt_type: str
    original_filename: Optional[str] = None

class UpdateSummaryRequest(BaseModel):
    summary_id: int
    content: str

PROMPTS = load_prompts()

@app.get("/api/prompts")
async def get_prompts():
    """Get list of available prompts"""
    return {
        "prompts": [
            {
                "id": name,
                "label": name.replace('_', ' ').title(),
                "description": get_prompt_content(name).split('\n')[0][:100] + '...'
            }
            for name in PROMPTS.keys()
            if name != 'base_prompt'
        ]
    }

@app.get("/api/prompts/{prompt_id}")
async def get_prompt(prompt_id: str):
    """Get specific prompt content"""
    if prompt_id not in PROMPTS:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return {"content": PROMPTS[prompt_id]}

@app.post("/api/summarize")
async def summarize_text(request: SummaryRequest):
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        base_prompt = PROMPTS.get('base_prompt', '')
        specific_prompt = PROMPTS.get(request.prompt_type, '')
        
        full_prompt = f"{base_prompt}\n\n{specific_prompt}"
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": full_prompt},
                {"role": "user", "content": request.text}
            ],
            max_tokens=2000,
            temperature=0.7
        )
        
        summary = response.choices[0].message.content
        
        # Save to database
        summary_id = db.save_summary(
            input_text=request.text,
            summary=summary,
            prompt_type=request.prompt_type,
            original_filename=request.original_filename
        )
        
        return {
            "summary": summary,
            "summary_id": summary_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload-audio")
async def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    try:
        # Create temp directory if it doesn't exist
        os.makedirs("temp", exist_ok=True)
        
        # Save uploaded file temporarily
        temp_path = f"temp/{file.filename}"
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Process the audio file
        transcript, failed_chunks = process_audio_file(temp_path)
        
        # Add cleanup task
        background_tasks.add_task(cleanup_temp_file, temp_path)
        
        if not transcript:
            raise HTTPException(status_code=400, detail="Failed to transcribe audio")
            
        return {
            "transcript": transcript,
            "failed_chunks": failed_chunks,
            "original_filename": file.filename
        }
        
    except Exception as e:
        # Clean up on error
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/summaries")
async def get_summaries(limit: int = 50, offset: int = 0):
    """Get recent summaries with pagination"""
    try:
        summaries = db.get_summaries(limit, offset)
        total = db.get_summaries_count()
        return {
            "summaries": summaries,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/summaries/{summary_id}")
async def get_summary(summary_id: int):
    """Get a specific summary and its versions"""
    try:
        summary = db.get_summary(summary_id)
        if not summary:
            raise HTTPException(status_code=404, detail="Summary not found")
            
        versions = db.get_summary_versions(summary_id)
        return {
            "summary": summary,
            "versions": versions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/summaries/{summary_id}/versions")
async def create_summary_version(summary_id: int, request: UpdateSummaryRequest):
    """Create a new version of a summary"""
    try:
        version_id = db.save_summary_version(
            summary_id=summary_id,
            content=request.content
        )
        return {"version_id": version_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
