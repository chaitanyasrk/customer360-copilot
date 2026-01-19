"""
Account Insights Service - AI-powered account activity analysis with batch processing
"""
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate

from app.core.config import settings
from app.models.account_insights_schemas import (
    SummaryFormat,
    AccountActivityData,
    AccountInsightsResponse,
    InsightSection,
    ChartData,
    BatchSummaryResult
)
from app.prompts.cot_template import (
    ACCOUNT_ACTIVITY_BATCH_PROMPT,
    ACCOUNT_ACTIVITY_FINAL_PROMPT
)
from app.services.salesforce_service import salesforce_service


class AccountInsightsService:
    """Service for generating AI-powered account activity insights"""
    
    BATCH_SIZE = 50  # Records per batch for LLM processing
    
    def __init__(self):
        """Initialize the service with LLM"""
        self.llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            temperature=0.3,
            google_api_key=settings.GOOGLE_API_KEY
        )
        print(f"📊 AccountInsightsService initialized with model: {settings.GEMINI_MODEL}")
        
        self.batch_prompt = PromptTemplate(
            template=ACCOUNT_ACTIVITY_BATCH_PROMPT,
            input_variables=[
                "account_name", "account_id", "batch_number", "total_batches",
                "start_date", "end_date", "record_count", "activities_data"
            ]
        )
        
        self.final_prompt = PromptTemplate(
            template=ACCOUNT_ACTIVITY_FINAL_PROMPT,
            input_variables=[
                "account_name", "account_id", "start_date", "end_date",
                "total_count", "task_count", "event_count", "case_count",
                "batch_summaries", "formats"
            ]
        )
    
    def _format_activities_for_prompt(self, activities: List[Dict[str, Any]]) -> str:
        """Format activity records for LLM prompt"""
        formatted = []
        for i, activity in enumerate(activities, 1):
            formatted.append(
                f"{i}. [{activity.get('type', 'Unknown')}] "
                f"Subject: {activity.get('subject', 'N/A')} | "
                f"Status: {activity.get('status', 'N/A')} | "
                f"Priority: {activity.get('priority', 'N/A')} | "
                f"Date: {activity.get('activity_date', 'N/A')} | "
                f"Owner: {activity.get('owner_name', 'N/A')}"
            )
        return "\n".join(formatted)
    
    async def _summarize_batch(
        self,
        activities: List[Dict[str, Any]],
        account_name: str,
        account_id: str,
        batch_number: int,
        total_batches: int,
        start_date: str,
        end_date: str
    ) -> BatchSummaryResult:
        """Summarize a single batch of activities"""
        try:
            activities_data = self._format_activities_for_prompt(activities)
            
            prompt = self.batch_prompt.format(
                account_name=account_name,
                account_id=account_id,
                batch_number=batch_number,
                total_batches=total_batches,
                start_date=start_date,
                end_date=end_date,
                record_count=len(activities),
                activities_data=activities_data
            )
            
            response = await self.llm.ainvoke(prompt)
            response_text = response.content
            
            # Parse JSON response
            try:
                # Clean up response if needed
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0]
                
                result = json.loads(response_text.strip())
                
                return BatchSummaryResult(
                    batch_number=batch_number,
                    record_count=len(activities),
                    summary=result.get("batch_summary", ""),
                    key_points=result.get("key_points", [])
                )
            except json.JSONDecodeError:
                # Fallback: use raw text as summary
                return BatchSummaryResult(
                    batch_number=batch_number,
                    record_count=len(activities),
                    summary=response_text[:500],
                    key_points=[]
                )
                
        except Exception as e:
            print(f"❌ Error in batch {batch_number}: {e}")
            return BatchSummaryResult(
                batch_number=batch_number,
                record_count=len(activities),
                summary=f"Error processing batch: {str(e)}",
                key_points=[]
            )
    
    async def _generate_final_insights(
        self,
        batch_summaries: List[BatchSummaryResult],
        account_name: str,
        account_id: str,
        start_date: str,
        end_date: str,
        task_count: int,
        event_count: int,
        case_count: int,
        formats: List[SummaryFormat]
    ) -> Dict[str, Any]:
        """Generate final consolidated insights from batch summaries"""
        try:
            # Format batch summaries for prompt
            summaries_text = ""
            for batch in batch_summaries:
                summaries_text += f"\n--- Batch {batch.batch_number} ({batch.record_count} records) ---\n"
                summaries_text += f"{batch.summary}\n"
                if batch.key_points:
                    summaries_text += "Key Points:\n"
                    for point in batch.key_points:
                        summaries_text += f"  - {point}\n"
            
            format_names = [f.value for f in formats]
            
            prompt = self.final_prompt.format(
                account_name=account_name,
                account_id=account_id,
                start_date=start_date,
                end_date=end_date,
                total_count=task_count + event_count + case_count,
                task_count=task_count,
                event_count=event_count,
                case_count=case_count,
                batch_summaries=summaries_text,
                formats=", ".join(format_names)
            )
            
            response = await self.llm.ainvoke(prompt)
            response_text = response.content
            
            # Parse JSON response
            try:
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0]
                
                return json.loads(response_text.strip())
            except json.JSONDecodeError:
                return {
                    "executive_summary": response_text[:500],
                    "sections": [],
                    "key_insights": []
                }
                
        except Exception as e:
            print(f"❌ Error generating final insights: {e}")
            return {
                "executive_summary": f"Error generating insights: {str(e)}",
                "sections": [],
                "key_insights": []
            }
    
    async def generate_insights(
        self,
        account_id: str,
        account_name: str,
        activities: Dict[str, Any],
        start_date: str,
        end_date: str,
        formats: List[SummaryFormat]
    ) -> AccountInsightsResponse:
        """
        Generate comprehensive account insights with batch processing
        
        Args:
            account_id: Salesforce Account ID
            account_name: Account name for display
            activities: Dictionary with tasks, events, cases lists
            start_date: Start date string
            end_date: End date string
            formats: List of requested output formats
        
        Returns:
            AccountInsightsResponse with summarized insights
        """
        # Combine all activities into one list for batch processing
        all_activities = (
            activities.get('tasks', []) +
            activities.get('events', []) +
            activities.get('cases', [])
        )
        
        total_count = len(all_activities)
        task_count = len(activities.get('tasks', []))
        event_count = len(activities.get('events', []))
        case_count = len(activities.get('cases', []))
        
        print(f"📊 Processing {total_count} activities for account {account_name}")
        
        # Batch processing
        batch_summaries = []
        if total_count > 0:
            import asyncio
            num_batches = (total_count + self.BATCH_SIZE - 1) // self.BATCH_SIZE
            
            # Check if parallel processing is enabled
            if settings.PARALLEL_BATCHES:
                print(f"  📦 Processing {num_batches} batches in PARALLEL")
                # Create all batch tasks
                batch_tasks = []
                for i in range(num_batches):
                    start_idx = i * self.BATCH_SIZE
                    end_idx = min((i + 1) * self.BATCH_SIZE, total_count)
                    batch = all_activities[start_idx:end_idx]
                    
                    task = self._summarize_batch(
                        activities=batch,
                        account_name=account_name,
                        account_id=account_id,
                        batch_number=i + 1,
                        total_batches=num_batches,
                        start_date=start_date,
                        end_date=end_date
                    )
                    batch_tasks.append(task)
                
                # Execute all batches in parallel
                batch_summaries = await asyncio.gather(*batch_tasks)
                print(f"  ✅ All {num_batches} batches complete")
            else:
                # Sequential processing with delay to avoid rate limits
                print(f"  📦 Processing {num_batches} batches SEQUENTIALLY (delay: {settings.BATCH_DELAY_SECONDS}s)")
                for i in range(num_batches):
                    start_idx = i * self.BATCH_SIZE
                    end_idx = min((i + 1) * self.BATCH_SIZE, total_count)
                    batch = all_activities[start_idx:end_idx]
                    
                    print(f"  ⏳ Processing batch {i + 1}/{num_batches}...")
                    summary = await self._summarize_batch(
                        activities=batch,
                        account_name=account_name,
                        account_id=account_id,
                        batch_number=i + 1,
                        total_batches=num_batches,
                        start_date=start_date,
                        end_date=end_date
                    )
                    batch_summaries.append(summary)
                    print(f"  ✅ Batch {i + 1} complete")
                    
                    # Add delay between batches to avoid rate limits (except after last batch)
                    if i < num_batches - 1:
                        print(f"  ⏸️ Waiting {settings.BATCH_DELAY_SECONDS}s before next batch...")
                        await asyncio.sleep(settings.BATCH_DELAY_SECONDS)
        
        # Generate final insights
        print("  🧠 Generating final consolidated insights...")
        final_result = await self._generate_final_insights(
            batch_summaries=batch_summaries,
            account_name=account_name,
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
            task_count=task_count,
            event_count=event_count,
            case_count=case_count,
            formats=formats
        )
        
        # Build response sections based on requested formats
        sections = []
        
        if SummaryFormat.POINTERS in formats:
            key_insights = final_result.get("key_insights", [])
            if key_insights:
                sections.append(InsightSection(
                    title="Key Insights",
                    format=SummaryFormat.POINTERS,
                    content=key_insights
                ))
        
        if SummaryFormat.TABLES in formats:
            table_data = final_result.get("table_data", {})
            if table_data:
                sections.append(InsightSection(
                    title="Activity Summary",
                    format=SummaryFormat.TABLES,
                    content=table_data
                ))
        
        # Add any additional sections from LLM response
        for section in final_result.get("sections", []):
            sections.append(InsightSection(
                title=section.get("title", "Section"),
                format=SummaryFormat(section.get("format", "pointers")),
                content=section.get("content", "")
            ))
        
        # Build chart data if requested
        charts = None
        if SummaryFormat.CHARTS in formats:
            chart_data = final_result.get("chart_data", {})
            charts = []
            
            # Activity by type chart
            if "activity_by_type" in chart_data:
                charts.append(ChartData(
                    title="Activities by Type",
                    chart_type="bar",
                    labels=chart_data["activity_by_type"].get("labels", ["Tasks", "Events", "Cases"]),
                    datasets=[{
                        "label": "Count",
                        "data": chart_data["activity_by_type"].get("values", [task_count, event_count, case_count]),
                        "backgroundColor": ["#3B82F6", "#10B981", "#F59E0B"]
                    }]
                ))
            
            # Activity by month chart
            if "activity_by_month" in chart_data:
                charts.append(ChartData(
                    title="Activity Trend",
                    chart_type="line",
                    labels=chart_data["activity_by_month"].get("labels", []),
                    datasets=[{
                        "label": "Activities",
                        "data": chart_data["activity_by_month"].get("values", []),
                        "borderColor": "#3B82F6",
                        "fill": False
                    }]
                ))
            
            # Status distribution chart
            if "status_distribution" in chart_data:
                charts.append(ChartData(
                    title="Status Distribution",
                    chart_type="pie",
                    labels=chart_data["status_distribution"].get("labels", []),
                    datasets=[{
                        "data": chart_data["status_distribution"].get("values", []),
                        "backgroundColor": ["#10B981", "#3B82F6", "#F59E0B"]
                    }]
                ))
        
        response = AccountInsightsResponse(
            account_id=account_id,
            account_name=account_name,
            date_range={"start": start_date, "end": end_date},
            total_activities=total_count,
            processing_info={
                "batch_size": self.BATCH_SIZE,
                "batches_processed": len(batch_summaries),
                "task_count": task_count,
                "event_count": event_count,
                "case_count": case_count
            },
            sections=sections,
            charts=charts,
            executive_summary=final_result.get("executive_summary", "No summary available."),
            generated_at=datetime.utcnow()
        )
        
        print(f"✅ Insights generated successfully for {account_name}")
        return response


# Singleton instance
account_insights_service = AccountInsightsService()
