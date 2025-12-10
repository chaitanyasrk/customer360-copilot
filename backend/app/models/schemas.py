"""
Pydantic models for request/response validation
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class CaseData(BaseModel):
    """Salesforce Case data model"""
    case_id: str = Field(..., description="Salesforce Case ID")
    case_number: str = Field(default="", description="User-visible Case Number")
    subject: str = Field(..., description="Case subject")
    description: str = Field(..., description="Case description")
    priority: str = Field(..., description="Case priority level")
    status: str = Field(..., description="Case status")
    is_closed: bool = Field(default=False, description="Whether the case is closed")
    created_date: str = Field(..., description="Case creation date")
    account_id: Optional[str] = None
    contact_id: Optional[str] = None
    account_data: Optional[Dict[str, Any]] = None
    contact_data: Optional[Dict[str, Any]] = None


class RelatedObjectData(BaseModel):
    """Related object data from Salesforce"""
    object_name: str
    records: List[Dict[str, Any]]


class CaseAnalysisRequest(BaseModel):
    """Request model for case analysis"""
    case_id: str
    include_related_objects: bool = True


class ReasoningSteps(BaseModel):
    """Chain-of-thought reasoning steps"""
    problem_understanding: Optional[str] = None
    data_analysis: Optional[str] = None
    key_insights: Optional[str] = None
    action_planning: Optional[str] = None


class CaseAnalysisResponse(BaseModel):
    """Response model for case analysis"""
    case_id: str
    reasoning_steps: Optional[ReasoningSteps] = None
    summary: str
    next_actions: List[str]
    priority_level: str
    estimated_resolution_time: Optional[str] = None
    required_teams: List[str] = []
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    raw_summary: str
    sanitized_summary: str
    accuracy_percentage: float = Field(..., ge=0.0, le=100.0)


class SanitizationLog(BaseModel):
    """Log entry for sanitization operations"""
    original: str
    sanitized: str
    type: str


class SanitizationRequest(BaseModel):
    """Request model for summary sanitization"""
    original_summary: str


class SanitizationResponse(BaseModel):
    """Response model for sanitization"""
    sanitized_summary: str
    sanitization_log: List[SanitizationLog]
    confidence_score: float


class AgentInfo(BaseModel):
    """Agent information model"""
    agent_id: str
    agent_name: str
    email: str
    skills: List[str]
    current_workload: int = 0
    availability_status: str = "available"


class AgentRecommendation(BaseModel):
    """Agent recommendation model"""
    agent_id: str
    agent_name: str
    match_score: float
    reasoning: str


class AgentAssignmentResponse(BaseModel):
    """Response model for agent assignment"""
    recommended_agent: AgentRecommendation
    backup_agents: List[AgentRecommendation]
    confidence_score: float


class ChatMessage(BaseModel):
    """Chat message model for WebSocket communication"""
    message_id: Optional[str] = None
    sender: str  # "user", "agent", "system"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    case_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TokenPayload(BaseModel):
    """JWT token payload"""
    sub: str  # subject (user_id or agent_id)
    exp: datetime
    role: str  # "user" or "agent"


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    version: str = "1.0.0"


class SaveSummaryRequest(BaseModel):
    """Request model for saving case summary"""
    summary: str
    additional_data: Optional[Dict[str, Any]] = None


class SaveSummaryResponse(BaseModel):
    """Response model for save summary operation"""
    success: bool
    record_id: Optional[str] = None
    message: str
    case_id: str
    action: Optional[str] = None
    error: Optional[str] = None


class CaseQueryRequest(BaseModel):
    """Request model for querying case details"""
    question: str


class CaseQueryResponse(BaseModel):
    """Response model for case query"""
    answer: str
    sources: List[str] = []
    confidence: float = 0.0
    case_id: str


class CaseClosedResponse(BaseModel):
    """Response model when attempting to analyze a closed case"""
    is_closed: bool = True
    case_number: str
    status: str
    message: str = "This case is closed. Analysis is not available for closed cases."
