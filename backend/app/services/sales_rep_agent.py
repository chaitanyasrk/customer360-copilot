"""
Sales Rep Summary Multi-Agent Pipeline

A LangGraph-based multi-agent system with 3 specialized agents:
1. Metadata Agent — discovers SF object schemas (cached)
2. Query Agent — uses LLM + metadata to formulate and execute SOQL
3. Insights Agent — generates structured Sales Rep summary from raw data
"""
import json
import re
from typing import Dict, Any, List, TypedDict, Optional
from datetime import datetime

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langgraph.graph import Graph, StateGraph

from app.core.config import settings
from app.services.metadata_cache import metadata_cache
from app.prompts.cot_template import (
    QUERY_FORMULATION_PROMPT,
    SALES_REP_SUMMARY_PROMPT,
)


# ---------------------------------------------------------------------------
# Shared pipeline state
# ---------------------------------------------------------------------------

class SalesRepSummaryState(TypedDict):
    """Shared state flowing through the 3-agent pipeline."""

    # ---- Inputs ----
    account_id: str
    account_name: str
    start_date: str
    end_date: str

    # ---- Metadata Agent outputs ----
    object_metadata: Dict[str, Any]       # {object_name: {fields, relationships, ...}}
    metadata_source: str                   # "cache" | "fresh"
    metadata_schema_text: str              # Compact text for LLM prompt

    # ---- Query Agent outputs ----
    generated_queries: Dict[str, str]     # {query_name: soql_string}
    raw_activities: List[Dict[str, Any]]  # Tasks + Events
    raw_cases: List[Dict[str, Any]]       # Cases
    raw_contacts: Dict[str, Dict[str, Any]]  # {contact_id: details}
    query_errors: List[str]

    # ---- Insights Agent outputs ----
    contact_interactions: List[Dict[str, Any]]
    case_trends: List[Dict[str, Any]]
    executive_summary: str
    key_takeaways: List[str]
    total_activities: int
    total_cases: int
    pipeline_info: Dict[str, Any]
    generated_at: str


# ---------------------------------------------------------------------------
# Multi-agent pipeline
# ---------------------------------------------------------------------------

class SalesRepSummaryAgent:
    """LangGraph multi-agent pipeline for Sales Rep account summaries."""

    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            temperature=0.3,
            google_api_key=settings.GOOGLE_API_KEY,
        )
        self.graph = self._build_graph()
        print(f"🤖 SalesRepSummaryAgent initialized with model: {settings.GEMINI_MODEL}")

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def _build_graph(self) -> Graph:
        workflow = StateGraph(SalesRepSummaryState)

        workflow.add_node("metadata_agent", self._metadata_agent)
        workflow.add_node("query_agent", self._query_agent)
        workflow.add_node("insights_agent", self._insights_agent)

        workflow.set_entry_point("metadata_agent")
        workflow.add_edge("metadata_agent", "query_agent")
        workflow.add_edge("query_agent", "insights_agent")
        workflow.set_finish_point("insights_agent")

        return workflow.compile()

    # ------------------------------------------------------------------
    # Node 1 — Metadata Agent
    # ------------------------------------------------------------------

    def _metadata_agent(self, state: SalesRepSummaryState) -> dict:
        """
        Discovers Salesforce object schemas via cached describe() metadata.
        Zero LLM calls. Zero SF calls on warm cache.
        """
        print("🔍 [Metadata Agent] Starting...")
        import time
        t0 = time.time()

        objects_needed = ["Task", "Event", "Case", "Contact", "Account"]
        object_metadata: Dict[str, Any] = {}
        source = "cache"

        for obj_name in objects_needed:
            md = metadata_cache.get_object_metadata(obj_name)
            if md:
                # Check if it was a fresh fetch (no timestamp in our cache before)
                object_metadata[obj_name] = md
            else:
                print(f"  ⚠️ Could not get metadata for {obj_name}")

        # Build compact schema text for the Query Agent's LLM prompt
        schema_text = metadata_cache.get_metadata_for_prompt(objects_needed)

        elapsed = time.time() - t0
        print(f"🔍 [Metadata Agent] Complete — {len(object_metadata)} objects in {elapsed:.2f}s")

        return {
            "object_metadata": object_metadata,
            "metadata_source": source,
            "metadata_schema_text": schema_text,
        }

    # ------------------------------------------------------------------
    # Node 2 — Query Agent
    # ------------------------------------------------------------------

    def _query_agent(self, state: SalesRepSummaryState) -> dict:
        """
        Uses LLM + cached metadata to formulate SOQL queries,
        validates them, and executes against Salesforce.
        """
        print("📝 [Query Agent] Starting...")
        import time
        t0 = time.time()

        account_id = state["account_id"]
        start_date = state["start_date"]
        end_date = state["end_date"]
        schema_text = state["metadata_schema_text"]

        generated_queries: Dict[str, str] = {}
        raw_activities: List[Dict[str, Any]] = []
        raw_cases: List[Dict[str, Any]] = []
        raw_contacts: Dict[str, Dict[str, Any]] = {}
        query_errors: List[str] = []

        # Step 1: Ask LLM to formulate SOQL queries
        try:
            prompt = PromptTemplate(
                template=QUERY_FORMULATION_PROMPT,
                input_variables=[
                    "account_id", "start_date", "end_date", "metadata_schema",
                ],
            )
            prompt_text = prompt.format(
                account_id=account_id,
                start_date=start_date,
                end_date=end_date,
                metadata_schema=schema_text,
            )

            response = self.llm.invoke(prompt_text)
            response_text = response.content

            # Parse JSON from LLM response
            queries_json = self._extract_json(response_text)
            if queries_json:
                generated_queries = queries_json
                print(f"  ✅ LLM generated {len(generated_queries)} queries")
            else:
                print("  ⚠️ LLM did not return valid JSON — using fallback queries")
                generated_queries = self._get_fallback_queries(
                    account_id, start_date, end_date, state.get("object_metadata", {})
                )

        except Exception as e:
            print(f"  ❌ LLM query generation failed: {e}")
            query_errors.append(f"LLM query generation: {str(e)}")
            generated_queries = self._get_fallback_queries(
                account_id, start_date, end_date, state.get("object_metadata", {})
            )

        # Step 2: Validate queries (safety check)
        for name, soql in list(generated_queries.items()):
            if not self._validate_soql(soql):
                print(f"  ⚠️ Invalid query '{name}' removed: {soql[:80]}...")
                query_errors.append(f"Invalid query '{name}': {soql[:100]}")
                del generated_queries[name]

        # Step 3: Execute queries
        from app.services.salesforce_service import salesforce_service

        if not salesforce_service.sf:
            print("  ❌ Salesforce not connected — cannot execute queries")
            query_errors.append("Salesforce not connected")
        else:
            # Execute Tasks query
            if "tasks_query" in generated_queries:
                try:
                    result = salesforce_service.sf.query(generated_queries["tasks_query"])
                    for record in result.get("records", []):
                        raw_activities.append(self._flatten_record(record, "Task"))
                    print(f"  📋 Tasks: {len(result.get('records', []))} records")
                except Exception as e:
                    print(f"  ⚠️ Tasks query error: {e}")
                    query_errors.append(f"Tasks query: {str(e)}")

            # Execute Events query
            if "events_query" in generated_queries:
                try:
                    result = salesforce_service.sf.query(generated_queries["events_query"])
                    for record in result.get("records", []):
                        raw_activities.append(self._flatten_record(record, "Event"))
                    print(f"  📅 Events: {len(result.get('records', []))} records")
                except Exception as e:
                    print(f"  ⚠️ Events query error: {e}")
                    query_errors.append(f"Events query: {str(e)}")

            # Execute Cases query
            if "cases_query" in generated_queries:
                try:
                    result = salesforce_service.sf.query(generated_queries["cases_query"])
                    for record in result.get("records", []):
                        raw_cases.append(self._flatten_record(record, "Case"))
                    print(f"  📁 Cases: {len(result.get('records', []))} records")
                except Exception as e:
                    print(f"  ⚠️ Cases query error: {e}")
                    query_errors.append(f"Cases query: {str(e)}")

            # Execute Contacts query (if provided)
            if "contacts_query" in generated_queries:
                try:
                    result = salesforce_service.sf.query(generated_queries["contacts_query"])
                    for record in result.get("records", []):
                        flat = self._flatten_record(record, "Contact")
                        contact_id = flat.get("Id", "")
                        if contact_id:
                            raw_contacts[contact_id] = flat
                    print(f"  👤 Contacts: {len(raw_contacts)} records")
                except Exception as e:
                    print(f"  ⚠️ Contacts query error: {e}")
                    query_errors.append(f"Contacts query: {str(e)}")

            # Also extract contact IDs from activities and fetch missing ones
            contact_ids_in_activities = set()
            for activity in raw_activities:
                who_id = activity.get("WhoId") or activity.get("Who.Id")
                if who_id and who_id not in raw_contacts:
                    contact_ids_in_activities.add(who_id)

            if contact_ids_in_activities and salesforce_service.sf:
                try:
                    ids_str = "','".join(contact_ids_in_activities)
                    contact_query = f"SELECT Id, Name, Title, Email, Phone, Department FROM Contact WHERE Id IN ('{ids_str}')"
                    result = salesforce_service.sf.query(contact_query)
                    for record in result.get("records", []):
                        flat = self._flatten_record(record, "Contact")
                        raw_contacts[flat.get("Id", "")] = flat
                    print(f"  👤 Additional contacts from activities: {len(result.get('records', []))}")
                except Exception as e:
                    print(f"  ⚠️ Additional contacts query error: {e}")

        elapsed = time.time() - t0
        print(f"📝 [Query Agent] Complete — {len(raw_activities)} activities, {len(raw_cases)} cases in {elapsed:.2f}s")

        return {
            "generated_queries": generated_queries,
            "raw_activities": raw_activities,
            "raw_cases": raw_cases,
            "raw_contacts": raw_contacts,
            "query_errors": query_errors,
        }

    # ------------------------------------------------------------------
    # Node 3 — Insights Agent
    # ------------------------------------------------------------------

    def _insights_agent(self, state: SalesRepSummaryState) -> dict:
        """
        Generates the structured Sales Rep summary from raw data using LLM.
        """
        print("📊 [Insights Agent] Starting...")
        import time
        t0 = time.time()

        raw_activities = state.get("raw_activities", [])
        raw_cases = state.get("raw_cases", [])
        raw_contacts = state.get("raw_contacts", {})
        account_name = state["account_name"]
        start_date = state["start_date"]
        end_date = state["end_date"]

        # Format data for prompt
        activities_text = self._format_data_for_prompt(raw_activities, "Activities", max_records=100)
        cases_text = self._format_data_for_prompt(raw_cases, "Cases", max_records=100)
        contacts_text = self._format_contacts_for_prompt(raw_contacts)

        # Define the output schema for the LLM
        output_schema = json.dumps({
            "contact_interactions": [
                {
                    "contact_name": "string",
                    "contact_title": "string or null",
                    "contact_email": "string or null",
                    "interaction_count": "integer",
                    "last_interaction_date": "YYYY-MM-DD or null",
                    "topics": ["topic1", "topic2"],
                    "activity_types": ["Call", "Email", "Meeting"],
                }
            ],
            "case_trends": [
                {
                    "category": "string (e.g. Credit Request, Ordering Issue)",
                    "count": "integer",
                    "percentage": "float (0-100)",
                    "trend": "rising | stable | declining",
                    "recent_examples": ["case subject 1", "case subject 2"],
                }
            ],
            "executive_summary": "2-4 sentence overview for the sales rep",
            "key_takeaways": [
                "Actionable insight 1",
                "Actionable insight 2",
            ],
        }, indent=2)

        try:
            prompt = PromptTemplate(
                template=SALES_REP_SUMMARY_PROMPT,
                input_variables=[
                    "account_name", "start_date", "end_date",
                    "activities_data", "cases_data", "contacts_data",
                    "output_schema", "total_activities", "total_cases",
                ],
            )
            prompt_text = prompt.format(
                account_name=account_name,
                start_date=start_date,
                end_date=end_date,
                activities_data=activities_text,
                cases_data=cases_text,
                contacts_data=contacts_text,
                output_schema=output_schema,
                total_activities=len(raw_activities),
                total_cases=len(raw_cases),
            )

            response = self.llm.invoke(prompt_text)
            result = self._extract_json(response.content)

            if not result:
                print("  ⚠️ LLM did not return valid JSON — using fallback")
                result = self._get_fallback_insights(raw_activities, raw_cases, raw_contacts)

        except Exception as e:
            print(f"  ❌ Insights generation failed: {e}")
            result = self._get_fallback_insights(raw_activities, raw_cases, raw_contacts)

        elapsed = time.time() - t0
        print(f"📊 [Insights Agent] Complete in {elapsed:.2f}s")

        # Build pipeline info
        pipeline_info = {
            "metadata_source": state.get("metadata_source", "unknown"),
            "queries_generated": len(state.get("generated_queries", {})),
            "query_errors": state.get("query_errors", []),
            "activities_fetched": len(raw_activities),
            "cases_fetched": len(raw_cases),
            "contacts_resolved": len(raw_contacts),
        }

        return {
            "contact_interactions": result.get("contact_interactions", []),
            "case_trends": result.get("case_trends", []),
            "executive_summary": result.get("executive_summary", "No summary available."),
            "key_takeaways": result.get("key_takeaways", []),
            "total_activities": len(raw_activities),
            "total_cases": len(raw_cases),
            "pipeline_info": pipeline_info,
            "generated_at": datetime.utcnow().isoformat(),
        }

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def generate_summary(
        self,
        account_id: str,
        account_name: str,
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """
        Run the full multi-agent pipeline and return the summary.

        Args:
            account_id: Salesforce Account ID
            account_name: Display name for the account
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD

        Returns:
            Dict matching SalesRepSummaryResponse schema
        """
        import time
        t0 = time.time()
        print(f"\n{'='*60}")
        print(f"🚀 Sales Rep Summary Pipeline — {account_name}")
        print(f"   Account: {account_id}")
        print(f"   Period:  {start_date} → {end_date}")
        print(f"{'='*60}")

        initial_state: SalesRepSummaryState = {
            "account_id": account_id,
            "account_name": account_name,
            "start_date": start_date,
            "end_date": end_date,
            "object_metadata": {},
            "metadata_source": "",
            "metadata_schema_text": "",
            "generated_queries": {},
            "raw_activities": [],
            "raw_cases": [],
            "raw_contacts": {},
            "query_errors": [],
            "contact_interactions": [],
            "case_trends": [],
            "executive_summary": "",
            "key_takeaways": [],
            "total_activities": 0,
            "total_cases": 0,
            "pipeline_info": {},
            "generated_at": "",
        }

        final_state = self.graph.invoke(initial_state)

        total_elapsed = time.time() - t0
        print(f"\n✅ Pipeline complete in {total_elapsed:.2f}s")

        # Add timing to pipeline info
        pipeline_info = final_state.get("pipeline_info", {})
        pipeline_info["total_elapsed_seconds"] = round(total_elapsed, 2)

        return {
            "account_id": account_id,
            "account_name": account_name,
            "date_range": {"start": start_date, "end": end_date},
            "contact_interactions": final_state.get("contact_interactions", []),
            "case_trends": final_state.get("case_trends", []),
            "total_activities": final_state.get("total_activities", 0),
            "total_cases": final_state.get("total_cases", 0),
            "executive_summary": final_state.get("executive_summary", ""),
            "key_takeaways": final_state.get("key_takeaways", []),
            "pipeline_info": pipeline_info,
            "generated_at": final_state.get("generated_at", datetime.utcnow().isoformat()),
        }

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON object from LLM response text."""
        try:
            # Try to find ```json ... ``` block
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            return json.loads(text.strip())
        except (json.JSONDecodeError, IndexError):
            # Try to find raw JSON
            try:
                match = re.search(r"\{.*\}", text, re.DOTALL)
                if match:
                    return json.loads(match.group())
            except (json.JSONDecodeError, AttributeError):
                pass
        return None

    def _validate_soql(self, soql: str) -> bool:
        """Basic SOQL validation — ensure it's a SELECT query, no DML."""
        soql_upper = soql.strip().upper()
        # Must start with SELECT
        if not soql_upper.startswith("SELECT"):
            return False
        # Must not contain DML keywords
        dml_keywords = ["INSERT", "UPDATE", "DELETE", "UPSERT", "MERGE", "UNDELETE"]
        for keyword in dml_keywords:
            if f" {keyword} " in soql_upper or soql_upper.startswith(keyword):
                return False
        return True

    def _flatten_record(self, record: Dict[str, Any], record_type: str) -> Dict[str, Any]:
        """
        Flatten a Salesforce query record, resolving nested relationship objects
        (e.g., Owner.Name, Who.Name) into dot-notation keys.
        """
        flat: Dict[str, Any] = {"_type": record_type}
        for key, value in record.items():
            if key == "attributes":
                continue
            if isinstance(value, dict) and "attributes" in value:
                # Nested relationship object — flatten it
                for sub_key, sub_val in value.items():
                    if sub_key != "attributes":
                        flat[f"{key}.{sub_key}"] = sub_val
            else:
                flat[key] = value
        return flat

    def _format_data_for_prompt(
        self, records: List[Dict[str, Any]], label: str, max_records: int = 100
    ) -> str:
        """Format raw records into a text block for the LLM prompt."""
        if not records:
            return f"No {label.lower()} found."

        truncated = records[:max_records]
        lines = [f"--- {label} ({len(records)} total, showing {len(truncated)}) ---"]
        for i, record in enumerate(truncated, 1):
            parts = []
            for k, v in record.items():
                if k.startswith("_") or v is None:
                    continue
                parts.append(f"{k}: {v}")
            lines.append(f"{i}. {' | '.join(parts)}")
        return "\n".join(lines)

    def _format_contacts_for_prompt(self, contacts: Dict[str, Dict[str, Any]]) -> str:
        """Format contact details for the LLM prompt."""
        if not contacts:
            return "No contact details available."

        lines = [f"--- Contacts ({len(contacts)} total) ---"]
        for cid, contact in contacts.items():
            parts = []
            for k, v in contact.items():
                if k.startswith("_") or v is None:
                    continue
                parts.append(f"{k}: {v}")
            lines.append(f"- {' | '.join(parts)}")
        return "\n".join(lines)

    def _get_fallback_queries(
        self,
        account_id: str,
        start_date: str,
        end_date: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, str]:
        """
        Generate safe fallback SOQL queries using metadata to pick available fields.
        Only uses fields confirmed to exist in the metadata.
        """
        def _pick_fields(obj_name: str, desired: List[str]) -> List[str]:
            md = metadata.get(obj_name, {})
            available = {f["name"] for f in md.get("fields", [])}
            # Always include Id
            picked = ["Id"]
            for f in desired:
                # Handle relationship fields like Owner.Name
                base_field = f.split(".")[0]
                if base_field in available or f in available:
                    picked.append(f)
            return list(dict.fromkeys(picked))  # dedupe preserving order

        # Task fields
        task_fields = _pick_fields("Task", [
            "Subject", "Description", "Status", "Priority",
            "ActivityDate", "CreatedDate", "WhoId",
            "Owner.Name", "Who.Name",
        ])
        tasks_query = (
            f"SELECT {', '.join(task_fields)} FROM Task "
            f"WHERE AccountId = '{account_id}' "
            f"AND CreatedDate >= {start_date}T00:00:00Z "
            f"AND CreatedDate <= {end_date}T23:59:59Z "
            f"ORDER BY CreatedDate DESC"
        )

        # Event fields
        event_fields = _pick_fields("Event", [
            "Subject", "Description", "StartDateTime", "EndDateTime",
            "CreatedDate", "WhoId",
            "Owner.Name", "Who.Name", "Location",
        ])
        events_query = (
            f"SELECT {', '.join(event_fields)} FROM Event "
            f"WHERE AccountId = '{account_id}' "
            f"AND CreatedDate >= {start_date}T00:00:00Z "
            f"AND CreatedDate <= {end_date}T23:59:59Z "
            f"ORDER BY CreatedDate DESC"
        )

        # Case fields
        case_fields = _pick_fields("Case", [
            "CaseNumber", "Subject", "Description", "Status", "Priority",
            "Type", "Reason", "Origin", "CreatedDate", "ClosedDate",
            "Owner.Name",
        ])
        cases_query = (
            f"SELECT {', '.join(case_fields)} FROM Case "
            f"WHERE AccountId = '{account_id}' "
            f"AND CreatedDate >= {start_date}T00:00:00Z "
            f"AND CreatedDate <= {end_date}T23:59:59Z "
            f"ORDER BY CreatedDate DESC"
        )

        # Contacts query — will be supplemented after activities
        contact_fields = _pick_fields("Contact", [
            "Name", "Title", "Email", "Phone", "Department",
        ])
        contacts_query = (
            f"SELECT {', '.join(contact_fields)} FROM Contact "
            f"WHERE AccountId = '{account_id}'"
        )

        return {
            "tasks_query": tasks_query,
            "events_query": events_query,
            "cases_query": cases_query,
            "contacts_query": contacts_query,
        }

    def _get_fallback_insights(
        self,
        activities: List[Dict[str, Any]],
        cases: List[Dict[str, Any]],
        contacts: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate basic insights without LLM as a fallback."""
        # Build contact interactions from raw data
        contact_map: Dict[str, Dict[str, Any]] = {}
        for activity in activities:
            who_name = activity.get("Who.Name") or activity.get("WhoName") or "Unknown"
            who_id = activity.get("WhoId") or ""
            if who_name == "Unknown" and not who_id:
                continue

            key = who_id or who_name
            if key not in contact_map:
                contact_detail = contacts.get(who_id, {})
                contact_map[key] = {
                    "contact_name": contact_detail.get("Name", who_name),
                    "contact_title": contact_detail.get("Title"),
                    "contact_email": contact_detail.get("Email"),
                    "interaction_count": 0,
                    "last_interaction_date": None,
                    "topics": [],
                    "activity_types": [],
                }

            entry = contact_map[key]
            entry["interaction_count"] += 1

            subject = activity.get("Subject")
            if subject and subject not in entry["topics"]:
                entry["topics"].append(subject)

            act_type = activity.get("_type", "Activity")
            if act_type not in entry["activity_types"]:
                entry["activity_types"].append(act_type)

            act_date = (
                activity.get("ActivityDate")
                or activity.get("CreatedDate")
                or activity.get("StartDateTime")
            )
            if act_date:
                date_str = str(act_date)[:10]
                if not entry["last_interaction_date"] or date_str > entry["last_interaction_date"]:
                    entry["last_interaction_date"] = date_str

        # Build case trends from raw data
        case_categories: Dict[str, List[Dict[str, Any]]] = {}
        for case in cases:
            category = (
                case.get("Type")
                or case.get("Issue_Type__c")
                or case.get("Reason")
                or "Uncategorized"
            )
            if category not in case_categories:
                case_categories[category] = []
            case_categories[category].append(case)

        total_cases = len(cases)
        case_trends = []
        for cat, cat_cases in sorted(
            case_categories.items(), key=lambda x: len(x[1]), reverse=True
        ):
            case_trends.append({
                "category": cat,
                "count": len(cat_cases),
                "percentage": round(len(cat_cases) / total_cases * 100, 1) if total_cases else 0,
                "trend": "stable",
                "recent_examples": [c.get("Subject", "N/A") for c in cat_cases[:3]],
            })

        return {
            "contact_interactions": list(contact_map.values()),
            "case_trends": case_trends,
            "executive_summary": (
                f"Account has {len(activities)} activities and {total_cases} cases "
                f"in the selected period. {len(contact_map)} contacts were engaged."
            ),
            "key_takeaways": [
                f"Total of {len(activities)} activities recorded",
                f"{total_cases} cases logged across {len(case_categories)} categories",
                f"{len(contact_map)} unique contacts interacted with",
            ],
        }


# Singleton instance
sales_rep_agent = SalesRepSummaryAgent()
