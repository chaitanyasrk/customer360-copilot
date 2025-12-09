"""
FastAPI route handlers
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from typing import List
from datetime import datetime

from app.models.schemas import (
    CaseAnalysisRequest,
    CaseAnalysisResponse,
    AgentInfo,
    HealthResponse,
    TokenPayload
)
from app.core.auth import verify_token, verify_agent_token, create_access_token
from app.services.agent_service import agent_service

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="1.0.0"
    )


@router.get("/salesforce/health")
async def salesforce_health_check():
    """
    Salesforce connection health check endpoint
    
    Tests the Salesforce API connection and returns detailed status information.
    This endpoint does not require authentication and can be used to verify SF credentials.
    """
    from app.services.salesforce_service import salesforce_service
    
    # Use the dedicated health check method from the service
    health_status = salesforce_service.check_connection()
    
    # Add timestamp to the response
    health_status["timestamp"] = datetime.utcnow()
    
    return health_status


@router.post("/auth/token")
async def login(username: str, password: str, role: str = "agent"):
    """
    Generate JWT token for authentication
    
    For PoC, accepts any username/password
    In production, validate against Salesforce or user database
    """
    # TODO: Validate credentials against Salesforce
    # For PoC, accept any credentials
    
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    token = create_access_token(subject=username, role=role)
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": role
    }


@router.post("/cases/analyze", response_model=CaseAnalysisResponse)
async def analyze_case(
    request: CaseAnalysisRequest,
    token: TokenPayload = Depends(verify_agent_token)
):
    """
    Analyze a Salesforce case and generate summary with next actions
    
    Requires agent authentication
    """
    try:
        result = await agent_service.analyze_case(request.case_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing case: {str(e)}"
        )


@router.get("/agents/available", response_model=List[AgentInfo])
async def get_available_agents(token: TokenPayload = Depends(verify_token)):
    """
    Get list of available agents
    
    For PoC, returns mock data
    """
    # TODO: Fetch from Salesforce or agent management system
    mock_agents = [
        AgentInfo(
            agent_id="agent_001",
            agent_name="Sarah Johnson",
            email="sarah.j@company.com",
            skills=["Technical Support", "Billing", "API Integration"],
            current_workload=3,
            availability_status="available"
        ),
        AgentInfo(
            agent_id="agent_002",
            agent_name="Michael Chen",
            email="michael.c@company.com",
            skills=["Account Management", "Enterprise Support"],
            current_workload=5,
            availability_status="available"
        ),
        AgentInfo(
            agent_id="agent_003",
            agent_name="Emily Rodriguez",
            email="emily.r@company.com",
            skills=["Technical Support", "Product Training"],
            current_workload=2,
            availability_status="available"
        )
    ]
    
    return mock_agents


@router.post("/cases/{case_id}/notify-agents")
async def notify_agents(
    case_id: str,
    agent_ids: List[str],
    summary: str,
    token: TokenPayload = Depends(verify_agent_token)
):
    """
    Send case summary to selected agents
    
    For PoC, simulates notification
    """
    # TODO: Implement actual notification (email, Slack, etc.)
    
    return {
        "status": "success",
        "message": f"Summary sent to {len(agent_ids)} agent(s)",
        "case_id": case_id,
        "notified_agents": agent_ids,
        "timestamp": datetime.utcnow()
    }


@router.get("/cases/{case_id}")
async def get_case_details(
    case_id: str,
    token: TokenPayload = Depends(verify_token)
):
    """Get case details from Salesforce"""
    from app.services.salesforce_service import salesforce_service
    
    case_data = salesforce_service.get_case_by_id(case_id)
    if not case_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found"
        )
    
    related_data = salesforce_service.get_related_objects(case_id)
    
    return {
        "case": case_data,
        "related_objects": related_data
    }


@router.post("/cases/{case_id}/save-summary")
async def save_case_summary(
    case_id: str,
    request: dict,
    token: TokenPayload = Depends(verify_agent_token)
):
    """
    Save the AI-generated summary to a Salesforce custom object
    
    This endpoint saves the summary to the configured custom object in Salesforce,
    creating a new record or updating an existing one for the case.
    """
    from app.services.salesforce_service import salesforce_service
    
    summary = request.get("summary", "")
    additional_data = request.get("additional_data", None)
    
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Summary text is required"
        )
    
    result = salesforce_service.save_case_summary(
        case_id=case_id,
        summary=summary,
        additional_data=additional_data
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("message", "Failed to save summary")
        )
    
    return result


@router.post("/cases/{case_id}/query")
async def query_case(
    case_id: str,
    request: dict,
    token: TokenPayload = Depends(verify_agent_token)
):
    """
    Answer questions about a case using AI
    
    This endpoint allows agents to ask questions about a case and receive
    AI-generated answers based on the case data and related objects.
    """
    from app.services.agent_service import agent_service
    
    question = request.get("question", "")
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question is required"
        )
    
    try:
        result = await agent_service.answer_case_question(case_id, question)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing question: {str(e)}"
        )
