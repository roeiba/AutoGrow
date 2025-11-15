"""FastAPI application for Seed Planter API"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from config import config
from database import get_db, init_db
from db_models import User
from auth import get_current_active_user
from usage_metering import UsageMeteringService

# Import routers
from auth_routes import router as auth_router
from billing_routes import router as billing_router

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
    TaskStatusResponse,
    OAuthExchangeRequest,
    OAuthExchangeResponse
)
from seed_planter import SeedPlanter
from task_storage import task_storage


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

    # Initialize database
    logger.info("📊 Initializing database...")
    init_db()
    logger.info("✅ Database initialized")
    
    # Connect to Redis
    logger.info("🔴 Connecting to Redis...")
    await task_storage.connect()
    logger.info("✅ Redis connected")

    yield
    # Shutdown
    logger.info("👋 Seed Planter API shutting down...")
    await task_storage.disconnect()


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

# Include routers
app.include_router(auth_router)
app.include_router(billing_router)


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
async def plant_seed(
    request: PlantSeedRequest,
    req: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Plant a new project seed (requires authentication)

    This endpoint initiates the planting of a permanent project that will grow
    autonomously. Creates GitHub org, forks SeedGPT template, customizes with AI,
    sets up GCP, and deploys.

    Returns a task_id that can be used to poll for progress.
    Usage is metered and counts against your monthly quota.
    """

    logger.info(f"📥 Received plant seed request: {request.project_name}")
    logger.info(f"   User: {current_user.email}")
    logger.info(f"   Description: {request.project_description[:100]}...")
    logger.info(f"   Mode: {request.mode.value}")

    try:
        # Check and enforce usage quota
        metering_service = UsageMeteringService(db)
        metering_service.enforce_quota(current_user, operation_count=1)

        # Generate task ID
        import uuid
        task_id = str(uuid.uuid4())

        # Increment usage counters
        metering_service.increment_usage(
            user=current_user,
            ai_operations=1,
            projects=1,
            api_calls=1
        )
        
        # Create task in Redis
        await task_storage.create_task(task_id, {
            "project_name": request.project_name,
            "project_description": request.project_description,
            "user_email": request.user_email or current_user.email,
            "mode": request.mode.value,
            "message": "Initializing project creation...",
            "progress_percent": 0
        })

        # Create progress callback that updates Redis
        async def progress_callback(progress: ProjectProgress):
            await task_storage.update_progress(task_id, progress)

        # Start project planting in background
        async def plant_task():
            try:
                result = await seed_planter.plant_seed(
                    request.project_name,
                    request.project_description,
                    request.mode,
                    request.user_email or current_user.email,
                    progress_callback
                )
                await task_storage.complete_task(task_id, result)
            except Exception as e:
                logger.error(f"Task {task_id} failed: {str(e)}")
                await task_storage.fail_task(task_id, str(e))
        
        asyncio.create_task(plant_task())

        # Return immediate response with task ID
        response = PlantSeedResponse(
            task_id=task_id,
            status=ProjectStatus.INITIALIZING,
            created_at=datetime.utcnow(),
            estimated_completion_time=120,  # ~2 minutes
            message="Project creation started. Use task_id to poll for status."
        )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions (like quota exceeded)
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to plant seed: {str(e)}")


@app.get("/api/v1/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Get the status of a project creation task
    
    Poll this endpoint to check the progress of your project creation.
    The task will include progress updates and final results when completed.
    """
    
    logger.debug(f"📊 Task status request for: {task_id}")
    
    # Get task data from Redis
    task_data = await task_storage.get_task(task_id)
    
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Get latest progress
    progress_data = await task_storage.get_progress(task_id)
    
    # Merge task and progress data
    if progress_data:
        task_data.update(progress_data)
    
    # Convert status string to enum
    status = ProjectStatus(task_data.get("status", "initializing"))
    
    response = TaskStatusResponse(
        task_id=task_id,
        status=status,
        message=task_data.get("message", "Processing..."),
        progress_percent=task_data.get("progress_percent", 0),
        project_id=task_data.get("project_id"),
        project_name=task_data.get("project_name"),
        org_url=task_data.get("org_url"),
        repo_url=task_data.get("repo_url"),
        deployment_url=task_data.get("deployment_url"),
        gcp_project_id=task_data.get("gcp_project_id"),
        error_message=task_data.get("error_message"),
        created_at=task_data.get("created_at"),
        updated_at=task_data.get("updated_at"),
        completed_at=task_data.get("completed_at")
    )
    
    return response


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
    
    # Cloud Run uses PORT environment variable (defaults to 8080)
    # Always prioritize PORT over API_PORT for Cloud Run compatibility
    port = int(os.getenv("PORT", "8080"))
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info" if not config.api_debug else "debug"
    )
