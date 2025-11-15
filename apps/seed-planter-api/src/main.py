"""FastAPI application for Seed Planter API"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
from models import (
    PlantSeedRequest, 
    PlantSeedResponse, 
    ProjectDetails, 
    ProjectListResponse,
    ProjectStatus,
    ProjectProgress,
    OAuthExchangeRequest,
    OAuthExchangeResponse
)
from seed_planter import SeedPlanter


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, project_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[project_id] = websocket

    def disconnect(self, project_id: str):
        if project_id in self.active_connections:
            del self.active_connections[project_id]

    async def send_progress(self, progress: ProjectProgress):
        websocket = self.active_connections.get(progress.project_id)
        if websocket:
            try:
                await websocket.send_json(progress.model_dump(mode='json'))
            except:
                self.disconnect(progress.project_id)


manager = ConnectionManager()
seed_planter = SeedPlanter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management"""
    # Startup
    logger.info("🌱 Seed Planter API starting up...")
    logger.info(f"   Mode: {config.api_debug and 'DEBUG' or 'PRODUCTION'}")
    logger.info(f"   Host: {config.api_host}:{config.api_port}")
    yield
    # Shutdown
    logger.info("👋 Seed Planter API shutting down...")


app = FastAPI(
    title="SeedGPT Seed Planter API",
    description="API for planting and growing autonomous AI-driven projects",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - Allow all origins for now
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Must be False when using allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "SeedGPT Seed Planter API",
        "status": "healthy",
        "version": "1.0.0",
        "mode": "SaaS",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/v1/oauth/exchange", response_model=OAuthExchangeResponse)
async def exchange_oauth_code(request: OAuthExchangeRequest):
    """
    Exchange GitHub OAuth authorization code for access token
    
    This endpoint acts as a proxy to securely exchange the OAuth code
    for an access token without exposing the client secret to the frontend.
    """
    import httpx
    
    logger.info(f"🔐 OAuth token exchange request received")
    
    if not config.github_oauth_client_secret:
        raise HTTPException(
            status_code=503,
            detail="OAuth client secret not configured on server"
        )
    
    try:
        # Exchange code for token with GitHub
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
                json={
                    "client_id": config.github_oauth_client_id,
                    "client_secret": config.github_oauth_client_secret,
                    "code": request.code
                }
            )
            
            if response.status_code != 200:
                logger.error(f"GitHub OAuth exchange failed: {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to exchange authorization code with GitHub"
                )
            
            data = response.json()
            
            if "error" in data:
                logger.error(f"GitHub OAuth error: {data.get('error_description', data['error'])}")
                raise HTTPException(
                    status_code=400,
                    detail=data.get("error_description", data["error"])
                )
            
            logger.info(f"✅ OAuth token exchange successful")
            
            return OAuthExchangeResponse(
                access_token=data["access_token"],
                token_type=data.get("token_type", "bearer"),
                scope=data.get("scope", "")
            )
            
    except httpx.HTTPError as e:
        logger.error(f"HTTP error during OAuth exchange: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to communicate with GitHub: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during OAuth exchange: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during token exchange: {str(e)}"
        )


@app.post("/api/v1/projects", response_model=PlantSeedResponse)
async def plant_seed(request: PlantSeedRequest, req: Request):
    """
    Plant a new project seed
    
    This endpoint initiates the planting of a permanent project that will grow
    autonomously. Creates GitHub org, forks SeedGPT template, customizes with AI,
    sets up GCP, and deploys.
    """
    
    logger.info(f"📥 Received plant seed request: {request.project_name}")
    logger.info(f"   Description: {request.project_description[:100]}...")
    logger.info(f"   Mode: {request.mode.value}")
    
    try:
        # Generate project ID upfront
        import uuid
        project_id = str(uuid.uuid4())
        
        # Create progress callback
        async def progress_callback(progress: ProjectProgress):
            await manager.send_progress(progress)
        
        # Start project planting in background
        asyncio.create_task(
            seed_planter.plant_seed(
                request.project_name,
                request.project_description,
                request.mode,
                request.user_email,
                progress_callback
            )
        )
        
        # Return immediate response with correct WebSocket URL
        ws_protocol = "wss" if req.url.scheme == "https" else "ws"
        ws_host = req.url.netloc  # includes port if present
        
        response = PlantSeedResponse(
            project_id=project_id,
            status=ProjectStatus.INITIALIZING,
            created_at=datetime.utcnow(),
            websocket_url=f"{ws_protocol}://{ws_host}/api/v1/projects/{project_id}/ws",
            estimated_completion_time=120  # ~2 minutes
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to plant seed: {str(e)}")


@app.get("/api/v1/projects/{project_id}", response_model=ProjectDetails)
async def get_project(project_id: str):
    """Get details for a specific project"""
    
    details = await seed_planter.get_project_details(project_id)
    
    if not details:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return details


@app.get("/api/v1/projects", response_model=ProjectListResponse)
async def list_projects():
    """List all planted projects"""
    
    projects = await seed_planter.list_projects()
    
    return ProjectListResponse(
        projects=projects,
        total=len(projects)
    )


@app.websocket("/api/v1/projects/{project_id}/ws")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    """WebSocket endpoint for real-time project progress updates"""
    logger.info(f"🔌 WebSocket connection request for project: {project_id}")
    await manager.connect(project_id, websocket)
    logger.info(f"✅ WebSocket connected for project: {project_id}")
    
    try:
        while True:
            # Keep connection alive and handle ping/pong
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
                logger.debug(f"💓 Ping/pong for project: {project_id}")
            
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected for project: {project_id}")
        manager.disconnect(project_id)


@app.post("/api/v1/projects/{project_id}/transfer")
async def transfer_project(project_id: str, new_owner: str):
    """Transfer project ownership to user"""
    
    try:
        success = await seed_planter.transfer_ownership(project_id, new_owner)
        if success:
            return {"message": "Project transferred successfully"}
        else:
            raise HTTPException(status_code=400, detail="Transfer failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to transfer project: {str(e)}")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    import os
    
    # Cloud Run uses PORT environment variable
    port = int(os.getenv("PORT", config.api_port))
    
    uvicorn.run(
        app,
        host=config.api_host,
        port=port,
        log_level="info" if not config.api_debug else "debug"
    )
