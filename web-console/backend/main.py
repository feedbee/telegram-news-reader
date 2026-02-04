
import os
import json
import logging
import httpx
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
import base64
from auth import get_current_user
from storage import Storage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Web Console API Gateway")

# Allow CORS for development (local react dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TRANSFORM_URL = os.getenv("TRANSFORM_URL", "http://transform:8000")
CONFIG_PATH = os.getenv("CONFIG_PATH", "config.json")

# Initialize Storage
storage = Storage()

# 1. API - List Channels
@app.get("/api/channels")
async def get_channels(user: dict = Depends(get_current_user)):
    if not os.path.exists(CONFIG_PATH):
        raise HTTPException(status_code=404, detail="Config file not found")
    
    try:
        with open(CONFIG_PATH, 'r') as f:
            data = json.load(f)
            # Filter active channels
            channels = [ch for ch in data.get("channels", []) if ch.get("is_active", True)]
            return channels
    except Exception as e:
        logger.error(f"Error loading channels: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 2. API - Proxy to Transform Summarize
@app.get("/api/summarize")
async def proxy_summarize(request: Request, user: dict = Depends(get_current_user)):
    paramsCopy = dict(request.query_params)
    channel_id = paramsCopy.get("channel_id")
    
    if not channel_id:
        raise HTTPException(status_code=400, detail="channel_id is required")
    
    # If last_message_id is not provided, try to fetch from user metadata
    if not paramsCopy.get("last_message_id"):
        last_ids = storage.get_user_metadata(user["uid"]).get("last_message_ids", {})
        if channel_id in last_ids:
            paramsCopy["last_message_id"] = str(last_ids[channel_id])
            logger.info(f"Using stored last_message_id {paramsCopy['last_message_id']} for {channel_id}")

    url = f"{TRANSFORM_URL}/summarize"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.get(url, params=paramsCopy)
            
            if response.status_code == 200:
                # Update user metadata on success
                new_last_id = response.headers.get('X-META-LAST-MESSAGE-ID')

                if new_last_id:
                    try:
                        valid_id = int(new_last_id)
                        storage.update_user_metadata(user["uid"], f"last_message_ids.{channel_id}", valid_id)
                    except ValueError:
                        pass # Ignore if not an integer

            # Transfer content and headers (especially X-META)
            content = response.content
            headers = dict(response.headers)
            # Remove some headers that might conflict
            headers.pop("content-length", None)
            headers.pop("content-encoding", None)
            
            return Response(
                content=content,
                status_code=response.status_code,
                headers=headers,
                media_type=response.headers.get("content-type")
            )
        except Exception as e:
            logger.exception("Proxy error")
            raise HTTPException(status_code=500, detail=f"Error connecting to Transform service: {e}")

# 3. Health Check
@app.get("/health")
async def health():
    return {"status": "ok"}

# 4. Static Files (Frontend build)
# This should be at the end to not catch API routes
FRONTEND_BUILD_DIR = "static"
if os.path.exists(FRONTEND_BUILD_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_BUILD_DIR, html=True), name="static")
else:
    logger.warning(f"Frontend build directory '{FRONTEND_BUILD_DIR}' not found. Serving API only.")

# 5. User Sync Endpoint
@app.post("/api/users/sync")
async def sync_user(user: dict = Depends(get_current_user)):
    """
    Upsert user in DB and return metadata.
    """
    try:
        # Sync user profile (uid, email, display_name, photo_url) and update last_login_at
        full_user = storage.upsert_user(user)
        return {
            "status": "ok",
            "metadata": full_user.get("metadata", {})
        }
    except Exception as e:
        logger.error(f"Error syncing user: {e}")
        raise HTTPException(status_code=500, detail="Failed to sync user")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
