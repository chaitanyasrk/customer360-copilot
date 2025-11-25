"""
Main FastAPI application
"""
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import router
from app.api.websocket import websocket_endpoint

# Create FastAPI app
app = FastAPI(
    title="Customer 360 Copilot API",
    description="AI-powered Salesforce Customer 360 case management copilot",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api/v1", tags=["api"])


# WebSocket endpoint
@app.websocket("/ws/{role}/{user_id}")
async def websocket_route(websocket: WebSocket, role: str, user_id: str):
    """WebSocket endpoint for real-time communication"""
    await websocket_endpoint(websocket, role, user_id)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Customer 360 Copilot API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=True
    )
