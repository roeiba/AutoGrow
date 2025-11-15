"""FastAPI application for Sandbox API"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import config
from models import (
    SandboxRequest, 
    SandboxResponse, 
    SandboxDetails, 
    SandboxListResponse,
    SandboxStatus,
    SandboxProgress
)
from sandbox_manager import SandboxManager


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, sandbox_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[sandbox_id] = websocket

    def disconnect(self, sandbox_id: str):
        if sandbox_id in self.active_connections:
            del self.active_connections[sandbox_id]

    async def send_progress(self, progress: SandboxProgress):
        websocket = self.active_connections.get(progress.sandbox_id)
        if websocket:
            try:
                await websocket.send_json(progress.model_dump(mode='json'))
            except:
                self.disconnect(progress.sandbox_id)


manager = ConnectionManager()
sandbox_manager = SandboxManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management"""
    # Startup
    print("🚀 Sandbox API starting up...")
    yield
    # Shutdown
    print("👋 Sandbox API shutting down...")


app = FastAPI(
    title="SeedGPT Sandbox API",
    description="API for creating isolated preview environments with AI-generated demos",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "SeedGPT Sandbox API",
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/v1/sandboxes", response_model=SandboxResponse)
async def create_sandbox(request: SandboxRequest, req: Request):
    """
    Create a new sandbox environment
    
    This endpoint initiates the creation of an isolated demo environment where
    AI will generate a project structure, issues, and pull requests based on
    the provided project idea.
    """
    
    try:
        # Generate sandbox ID upfront
        import uuid
        sandbox_id = str(uuid.uuid4())
        
        # Create progress callback
        async def progress_callback(progress: SandboxProgress):
            await manager.send_progress(progress)
        
        # Start sandbox creation in background
        asyncio.create_task(
            sandbox_manager.create_sandbox(
                request.project_idea,
                progress_callback
            )
        )
        
        # Return immediate response
        response = SandboxResponse(
            sandbox_id=sandbox_id,
            status=SandboxStatus.INITIALIZING,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(seconds=config.sandbox_ttl),
            websocket_url=f"ws://{req.url.hostname}:{config.api_port}/api/v1/sandboxes/{sandbox_id}/ws"
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create sandbox: {str(e)}")


@app.get("/api/v1/sandboxes/{sandbox_id}", response_model=SandboxDetails)
async def get_sandbox(sandbox_id: str):
    """Get details for a specific sandbox"""
    
    details = await sandbox_manager.get_sandbox_details(sandbox_id)
    
    if not details:
        raise HTTPException(status_code=404, detail="Sandbox not found")
    
    return details


@app.get("/api/v1/sandboxes", response_model=SandboxListResponse)
async def list_sandboxes():
    """List all active sandboxes"""
    
    sandboxes = await sandbox_manager.list_active_sandboxes()
    
    return SandboxListResponse(
        sandboxes=sandboxes,
        total=len(sandboxes)
    )


@app.websocket("/api/v1/sandboxes/{sandbox_id}/ws")
async def websocket_endpoint(websocket: WebSocket, sandbox_id: str):
    """
    WebSocket endpoint for real-time progress updates
    
    Connect to this endpoint to receive live updates about sandbox creation progress.
    """
    
    await manager.connect(sandbox_id, websocket)
    
    try:
        # Keep connection alive and wait for messages
        while True:
            # Wait for any message (ping/pong)
            data = await websocket.receive_text()
            
            # Echo back to confirm connection
            await websocket.send_json({
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat()
            })
            
    except WebSocketDisconnect:
        manager.disconnect(sandbox_id)


@app.delete("/api/v1/sandboxes/{sandbox_id}")
async def delete_sandbox(sandbox_id: str):
    """Delete a sandbox (cleanup resources)"""
    
    try:
        await sandbox_manager._cleanup_sandbox(sandbox_id)
        return {"message": "Sandbox deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete sandbox: {str(e)}")


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
    uvicorn.run(
        "main:app",
        host=config.api_host,
        port=config.api_port,
        reload=config.api_debug
    )
