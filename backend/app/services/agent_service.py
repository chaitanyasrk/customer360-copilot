"""
LangGraph-based AI Agent service for case analysis
"""
import json
import pandas as pd
from typing import Dict, Any, List, TypedDict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langgraph.graph import Graph, StateGraph
from app.core.config import settings
from app.models.schemas import (
    CaseData,
    RelatedObjectData,
    CaseAnalysisResponse,
    SanitizationResponse,
    SanitizationLog
)
from app.prompts.cot_template import (
    CASE_ANALYSIS_COT_PROMPT,
    SANITIZATION_COT_PROMPT
)
from app.services.salesforce_service import salesforce_service
import re


class AgentState(TypedDict):
    """State for the LangGraph agent"""
    case_id: str
    case_data: Dict[str, Any]
    related_data: List[Dict[str, Any]]
    examples: str
    analysis_result: Dict[str, Any]
    raw_summary: str
    sanitized_summary: str
    confidence_score: float
    accuracy_percentage: float


class CaseAnalysisAgent:
    """LangGraph-based agent for case analysis"""
    
    def __init__(self):
        """Initialize the agent with LLM and graph"""
        self.llm = ChatGoogleGenerativeAI(
            #model="gemini-2.5-flash",
            model="gemini-2.5-flash-lite",
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.3
        )
        self.graph = self._build_graph()
        self.examples_df = self._load_examples()
    
    def _load_examples(self) -> pd.DataFrame:
        """Load few-shot examples from CSV"""
        try:
            return pd.read_csv('app/data/examples.csv')
        except Exception as e:
            print(f"Error loading examples: {e}")
            return pd.DataFrame()
    
    def _build_graph(self) -> Graph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("fetch_data", self._fetch_case_data)
        workflow.add_node("analyze_case", self._analyze_case)
        workflow.add_node("sanitize_summary", self._sanitize_summary)
        workflow.add_node("calculate_accuracy", self._calculate_accuracy)
        
        # Define edges
        workflow.set_entry_point("fetch_data")
        workflow.add_edge("fetch_data", "analyze_case")
        workflow.add_edge("analyze_case", "sanitize_summary")
        workflow.add_edge("sanitize_summary", "calculate_accuracy")
        workflow.set_finish_point("calculate_accuracy")
        
        return workflow.compile()
    
    def _fetch_case_data(self, state: AgentState) -> AgentState:
        """Fetch case and related objects data"""
        case_id = state["case_id"]
        
        # Fetch case data
        case_data = salesforce_service.get_case_by_id(case_id)
        related_data = salesforce_service.get_related_objects(case_id)
        
        # Format examples
        examples_text = self._format_examples()
        
        state["case_data"] = case_data.model_dump() if case_data else {}
        state["related_data"] = [rd.model_dump() for rd in related_data]
        state["examples"] = examples_text
        
        return state
    
    def _format_examples(self) -> str:
        """Format few-shot examples for prompt"""
        if self.examples_df.empty:
            return "No examples available."
        
        examples_text = ""
        for idx, row in self.examples_df.head(3).iterrows():
            examples_text += f"\n**Example {idx + 1}:**\n"
            examples_text += f"Case: {row['case_subject']}\n"
            examples_text += f"Priority: {row['case_priority']}\n"
            examples_text += f"Summary: {row['expected_summary']}\n"
            examples_text += f"Next Actions: {row['expected_next_actions']}\n"
        
        return examples_text
    
    def _analyze_case(self, state: AgentState) -> AgentState:
        """Analyze case using CoT prompting"""
        case_data = state["case_data"]
        related_data = state["related_data"]
        examples = state["examples"]
        
        # Format related data
        related_data_text = self._format_related_data(related_data)
        
        # Create prompt
        prompt = PromptTemplate(
            template=CASE_ANALYSIS_COT_PROMPT,
            input_variables=[
                "case_id", "subject", "description", "priority",
                "status", "created_date", "related_data", "examples"
            ]
        )
        
        # Run analysis
        chain = LLMChain(llm=self.llm, prompt=prompt)
        result = chain.run(
            case_id=case_data.get("case_id", ""),
            subject=case_data.get("subject", ""),
            description=case_data.get("description", ""),
            priority=case_data.get("priority", ""),
            status=case_data.get("status", ""),
            created_date=case_data.get("created_date", ""),
            related_data=related_data_text,
            examples=examples
        )
        
        # Parse JSON response
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                analysis_result = json.loads(json_match.group())
            else:
                analysis_result = self._create_fallback_analysis(case_data)
        except Exception as e:
            print(f"Error parsing analysis result: {e}")
            analysis_result = self._create_fallback_analysis(case_data)
        
        state["analysis_result"] = analysis_result
        state["raw_summary"] = analysis_result.get("summary", "")
        state["confidence_score"] = analysis_result.get("confidence_score", 0.85)
        
        return state
    
    def _format_related_data(self, related_data: List[Dict[str, Any]]) -> str:
        """Format related objects data for prompt"""
        formatted = ""
        for obj_data in related_data:
            formatted += f"\n**{obj_data['object_name']}:**\n"
            for record in obj_data['records']:
                formatted += f"  - {json.dumps(record, indent=4)}\n"
        return formatted
    
    def _sanitize_summary(self, state: AgentState) -> AgentState:
        """Sanitize summary to remove sensitive information"""
        raw_summary = state["raw_summary"]
        
        # Create sanitization prompt
        prompt = PromptTemplate(
            template=SANITIZATION_COT_PROMPT,
            input_variables=["original_summary"]
        )
        
        # Run sanitization
        chain = LLMChain(llm=self.llm, prompt=prompt)
        result = chain.run(original_summary=raw_summary)
        
        # Parse JSON response
        try:
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                sanitization_result = json.loads(json_match.group())
                state["sanitized_summary"] = sanitization_result.get(
                    "sanitized_summary",
                    raw_summary
                )
            else:
                state["sanitized_summary"] = self._basic_sanitization(raw_summary)
        except Exception as e:
            print(f"Error parsing sanitization result: {e}")
            state["sanitized_summary"] = self._basic_sanitization(raw_summary)
        
        return state
    
    def _basic_sanitization(self, text: str) -> str:
        """Basic regex-based sanitization as fallback"""
        # Email
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
        # Phone
        text = re.sub(r'\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}', '[PHONE]', text)
        # Account numbers (simple pattern)
        text = re.sub(r'\b\d{6,}\b', '[ACCOUNT_NUM]', text)
        return text
    
    def _calculate_accuracy(self, state: AgentState) -> AgentState:
        """Calculate accuracy percentage based on confidence and completeness"""
        confidence = state["confidence_score"]
        analysis_result = state["analysis_result"]
        
        # Simple heuristic: base accuracy on confidence and completeness
        completeness_score = 1.0
        
        # Check if all expected fields are present
        if not analysis_result.get("next_actions"):
            completeness_score *= 0.8
        if not analysis_result.get("required_teams"):
            completeness_score *= 0.9
        if not analysis_result.get("estimated_resolution_time"):
            completeness_score *= 0.95
        
        accuracy = confidence * completeness_score * 100
        state["accuracy_percentage"] = round(accuracy, 2)
        
        return state
    
    def _create_fallback_analysis(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback analysis if LLM parsing fails"""
        return {
            "reasoning_steps": {
                "problem_understanding": "Analysis in progress",
                "data_analysis": "Reviewing case details",
                "key_insights": "Gathering insights",
                "action_planning": "Planning next steps"
            },
            "summary": f"Case {case_data.get('case_id')} regarding {case_data.get('subject')} requires attention.",
            "next_actions": [
                "Review case details thoroughly",
                "Contact customer for additional information",
                "Escalate to appropriate team"
            ],
            "priority_level": case_data.get("priority", "Medium"),
            "estimated_resolution_time": "24-48 hours",
            "required_teams": ["Support"],
            "confidence_score": 0.75
        }
    
    async def analyze_case(self, case_id: str, case_data: Dict[str, Any] = None) -> CaseAnalysisResponse:
        """
        Main entry point for case analysis
        
        Args:
            case_id: Salesforce Case Number
            case_data: Optional pre-fetched case data from get_case_by_number()
        
        Returns:
            CaseAnalysisResponse with analysis results
        """
        # Build related data from pre-fetched case_data
        related_data = []
        if case_data:
            # Add account as related data if available
            if case_data.get('account'):
                related_data.append({
                    'object_name': 'Account',
                    'records': [case_data['account']]
                })
            
            # Add contact as related data if available
            if case_data.get('contact'):
                related_data.append({
                    'object_name': 'Contact',
                    'records': [case_data['contact']]
                })
        
        # Prepare case data for state
        state_case_data = {}
        if case_data and case_data.get('case'):
            state_case_data = case_data['case']
        
        # Format examples
        examples_text = self._format_examples()
        
        # Initialize state with pre-fetched data
        initial_state: AgentState = {
            "case_id": case_id,
            "case_data": state_case_data,
            "related_data": related_data,
            "examples": examples_text,
            "analysis_result": {},
            "raw_summary": "",
            "sanitized_summary": "",
            "confidence_score": 0.0,
            "accuracy_percentage": 0.0
        }
        
        # Skip fetch_data node if we already have data, go directly to analyze
        if case_data:
            # Run analysis directly
            state = self._analyze_case(initial_state)
            state = self._sanitize_summary(state)
            state = self._calculate_accuracy(state)
            final_state = state
        else:
            # Run the full graph (will fetch data)
            final_state = self.graph.invoke(initial_state)
        
        # Build response
        analysis_result = final_state["analysis_result"]
        
        return CaseAnalysisResponse(
            case_id=case_id,
            summary=analysis_result.get("summary", ""),
            next_actions=analysis_result.get("next_actions", []),
            priority_level=analysis_result.get("priority_level", "Medium"),
            estimated_resolution_time=analysis_result.get("estimated_resolution_time"),
            required_teams=analysis_result.get("required_teams", []),
            confidence_score=final_state["confidence_score"],
            raw_summary=final_state["raw_summary"],
            sanitized_summary=final_state["sanitized_summary"],
            accuracy_percentage=final_state["accuracy_percentage"]
        )
    
    async def answer_case_question(self, case_id: str, question: str) -> Dict[str, Any]:
        """
        Answer a question about a case using case data and related objects
        
        Args:
            case_id: Salesforce Case ID
            question: User's question about the case
        
        Returns:
            Dictionary with answer, sources, and confidence
        """
        # Fetch case data
        case_data = salesforce_service.get_case_by_id(case_id)
        related_data = salesforce_service.get_related_objects(case_id)
        
        if not case_data:
            return {
                "answer": f"Unable to find case with ID: {case_id}",
                "sources": [],
                "confidence": 0.0,
                "case_id": case_id
            }
        
        # Format context from case and related data
        context = self._build_qa_context(case_data, related_data)
        
        # Create Q&A prompt
        qa_prompt = f"""You are a helpful customer service AI assistant. Based on the following case information, answer the user's question accurately and concisely.

CASE INFORMATION:
{context}

USER QUESTION: {question}

Instructions:
1. Answer the question based ONLY on the provided case information
2. If the information is not available, say so clearly
3. Be concise but comprehensive
4. Identify which data sources you used to answer

Respond in JSON format:
{{
    "answer": "Your answer here",
    "sources": ["List of data sources used, e.g., 'Case Details', 'Account Information', 'Case Comments'"],
    "confidence": 0.0-1.0 (how confident you are in the answer based on available data)
}}
"""
        
        try:
            # Get response from LLM
            response = self.llm.invoke(qa_prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Parse JSON response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                result["case_id"] = case_id
                return result
            else:
                return {
                    "answer": response_text,
                    "sources": ["Case Data"],
                    "confidence": 0.7,
                    "case_id": case_id
                }
        except Exception as e:
            print(f"Error in Q&A: {e}")
            return {
                "answer": f"I encountered an error while processing your question: {str(e)}",
                "sources": [],
                "confidence": 0.0,
                "case_id": case_id
            }
    
    def _build_qa_context(self, case_data: CaseData, related_data: List) -> str:
        """Build context string for Q&A from case and related data"""
        context_parts = []
        
        # Add case details
        context_parts.append("=== CASE DETAILS ===")
        context_parts.append(f"Case ID: {case_data.case_id}")
        context_parts.append(f"Subject: {case_data.subject}")
        context_parts.append(f"Description: {case_data.description}")
        context_parts.append(f"Priority: {case_data.priority}")
        context_parts.append(f"Status: {case_data.status}")
        context_parts.append(f"Created Date: {case_data.created_date}")
        
        # Add related objects data
        for related_obj in related_data:
            obj_name = related_obj.object_name if hasattr(related_obj, 'object_name') else related_obj.get('object_name', 'Unknown')
            records = related_obj.records if hasattr(related_obj, 'records') else related_obj.get('records', [])
            
            context_parts.append(f"\n=== {obj_name.upper()} ===")
            for record in records:
                for key, value in record.items():
                    if key != 'Id' and value:
                        context_parts.append(f"{key}: {value}")
        
        return "\n".join(context_parts)


# Singleton instance
agent_service = CaseAnalysisAgent()

