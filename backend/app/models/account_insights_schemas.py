"""
Pydantic models for Account Activity Insights feature
"""
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import date, datetime
from enum import Enum


class SummaryFormat(str, Enum):
    """Supported summary output formats"""
    TABLES = "tables"
    POINTERS = "pointers"  # Bullet points
    CHARTS = "charts"


class AccountSearchRequest(BaseModel):
    """Request model for searching an account"""
    identifier: str = Field(..., description="Account ID or Account Name to search")


class AccountSearchResponse(BaseModel):
    """Response model for account search"""
    found: bool
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    account_type: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    billing_city: Optional[str] = None
    billing_state: Optional[str] = None
    billing_country: Optional[str] = None
    owner_name: Optional[str] = None
    message: Optional[str] = None


class DateRangeRequest(BaseModel):
    """Date range for activity filtering"""
    start_date: date = Field(..., description="Start date for activity range")
    end_date: date = Field(..., description="End date for activity range")


class AccountInsightsRequest(BaseModel):
    """Request model for generating account insights"""
    start_date: date = Field(..., description="Start date for activity range")
    end_date: date = Field(..., description="End date for activity range")
    formats: List[SummaryFormat] = Field(
        default=[SummaryFormat.POINTERS, SummaryFormat.TABLES],
        description="Output formats for the summary"
    )


class ActivityRecord(BaseModel):
    """Single activity record (Task, Event, etc.)"""
    id: str
    type: str  # "Task", "Event", "Case"
    subject: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    activity_date: Optional[str] = None
    created_date: Optional[str] = None
    owner_name: Optional[str] = None
    related_to: Optional[str] = None  # Related Account/Contact name


class AccountActivityData(BaseModel):
    """Container for all fetched account activities"""
    account_id: str
    account_name: str
    tasks: List[ActivityRecord] = []
    events: List[ActivityRecord] = []
    cases: List[ActivityRecord] = []
    total_count: int = 0
    date_range: Dict[str, str] = {}


class InsightSection(BaseModel):
    """A section of the insights output"""
    title: str
    format: SummaryFormat
    content: Any  # Can be string, list, or dict depending on format


class ChartDataPoint(BaseModel):
    """Data point for chart visualization"""
    label: str
    value: float
    category: Optional[str] = None


class ChartData(BaseModel):
    """Chart visualization data"""
    title: str
    chart_type: Literal["bar", "line", "pie"] = "bar"
    labels: List[str]
    datasets: List[Dict[str, Any]]


class AccountInsightsResponse(BaseModel):
    """Response model for account activity insights"""
    account_id: str
    account_name: str
    date_range: Dict[str, str]
    total_activities: int
    processing_info: Dict[str, Any] = Field(
        default_factory=dict,
        description="Info about batch processing if applicable"
    )
    sections: List[InsightSection] = []
    charts: Optional[List[ChartData]] = None
    executive_summary: str = Field(
        ..., 
        description="Brief executive summary of key insights"
    )
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class BatchSummaryResult(BaseModel):
    """Result from a single batch summarization"""
    batch_number: int
    record_count: int
    summary: str
    key_points: List[str] = []
