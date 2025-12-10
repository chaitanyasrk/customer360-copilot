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


@router.post("/cases/analyze")
async def analyze_case(
    request: CaseAnalysisRequest,
    token: TokenPayload = Depends(verify_agent_token)
):
    """
    Analyze a Salesforce case and generate summary with next actions
    
    Requires agent authentication.
    Returns an error if the case is closed.
    """
    from app.services.salesforce_service import salesforce_service
    
    try:
        # First, fetch case data to check if it's closed
        case_data = salesforce_service.get_case_by_number(request.case_id)
        
        if not case_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case with number '{request.case_id}' not found. Please verify the case number."
            )
        
        # Check if case is closed
        # if case_data['case']['is_closed']:
        #     return {
        #         "is_closed": True,
        #         "case_number": case_data['case']['case_number'],
        #         "status": case_data['case']['status'],
        #         "message": "This case is closed. Analysis is not available for closed cases.",
        #         "closed_date": case_data['case'].get('closed_date')
        #     }
        
        # Proceed with analysis for open cases
        result = await agent_service.analyze_case(
            case_id=request.case_id,
            case_data=case_data
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing case: {str(e)}"
        )


@router.get("/agents/available", response_model=List[AgentInfo])
async def get_available_agents(
    case_number: str = None,
    token: TokenPayload = Depends(verify_token)
):
    """
    Get list of available agents from Salesforce
    
    If case_number is provided, includes the case owner as the first agent.
    Also returns top 3 active standard users.
    """
    from app.services.salesforce_service import salesforce_service
    
    agents = []
    owner_id = None
    
    # If case_number provided, get the case owner first
    if case_number:
        case_data = salesforce_service.get_case_by_number(case_number)
        if case_data and case_data.get('owner'):
            owner = case_data['owner']
            owner_id = owner.get('id')
            agents.append(AgentInfo(
                agent_id=owner.get('id', ''),
                agent_name=owner.get('name', 'Unknown'),
                email=owner.get('email', ''),
                skills=["Case Owner"],
                current_workload=0,
                availability_status="available"
            ))
    
    # Get additional active users (excluding the owner if present)
    active_users = salesforce_service.get_active_users(limit=3, exclude_user_id=owner_id)
    
    for user in active_users:
        agents.append(AgentInfo(
            agent_id=user.get('id', ''),
            agent_name=user.get('name', 'Unknown'),
            email=user.get('email', ''),
            skills=["Support Agent"],
            current_workload=0,
            availability_status="available"
        ))
    
    return agents



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
