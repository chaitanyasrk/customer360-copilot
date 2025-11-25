"""
Chain-of-Thought (CoT) Prompt Templates for Customer 360 Copilot
"""

CASE_ANALYSIS_COT_PROMPT = """You are an expert AI assistant helping customer service agents analyze Salesforce cases efficiently.

Given a case and its related objects data, perform a comprehensive analysis using step-by-step reasoning.

**Case Information:**
- Case ID: {case_id}
- Subject: {subject}
- Description: {description}
- Priority: {priority}
- Status: {status}
- Created Date: {created_date}

**Related Objects Data:**
{related_data}

**Few-Shot Examples:**
{examples}

**Analysis Instructions:**
Follow this chain-of-thought reasoning process:

1. **UNDERSTAND THE PROBLEM:**
   - What is the customer's main issue or request?
   - What is the urgency level based on priority and case details?
   - Are there any critical keywords or patterns?

2. **ANALYZE RELATED DATA:**
   - What relevant information is available from Account, Contact, and other related objects?
   - Are there any historical patterns or previous interactions?
   - What context does the email/comment history provide?

3. **IDENTIFY KEY INSIGHTS:**
   - What are the root causes or contributing factors?
   - Are there any dependencies or blockers?
   - What resources or teams might be needed?

4. **DETERMINE NEXT ACTIONS:**
   - What immediate steps should be taken?
   - What is the priority order of actions?
   - Who should be involved or notified?
   - What is the expected timeline?

5. **PREPARE SUMMARY:**
   - Create a concise summary highlighting key points
   - Ensure clarity and actionability
   - Include relevant context without overwhelming details

**Output Format:**
Provide your response in the following JSON structure:
{{
  "reasoning_steps": {{
    "problem_understanding": "...",
    "data_analysis": "...",
    "key_insights": "...",
    "action_planning": "..."
  }},
  "summary": "A clear, concise summary of the case with relevant context",
  "next_actions": [
    "Action 1 with specific details",
    "Action 2 with specific details",
    "Action 3 with specific details"
  ],
  "priority_level": "Critical|High|Medium|Low",
  "estimated_resolution_time": "...",
  "required_teams": ["team1", "team2"],
  "confidence_score": 0.95
}}

Think step-by-step and provide comprehensive reasoning before generating the final summary and action items.
"""

SANITIZATION_COT_PROMPT = """You are an expert AI assistant specializing in data sanitization and privacy protection.

Your task is to sanitize the following case summary by removing or masking sensitive information while preserving the essential context and actionability.

**Original Summary:**
{original_summary}

**Sensitive Data Patterns to Remove/Mask:**
- Email addresses
- Phone numbers
- Account numbers
- Credit card numbers
- Social Security Numbers (SSN)
- Passwords or tokens
- API keys
- Personal identifiable information (PII)
- Any other confidential business data

**Sanitization Instructions:**
Follow this chain-of-thought reasoning process:

1. **IDENTIFY SENSITIVE DATA:**
   - Scan the summary for patterns matching sensitive data types
   - Identify explicit mentions of confidential information
   - Look for context clues that might reveal sensitive details

2. **DETERMINE SANITIZATION STRATEGY:**
   - Decide whether to mask, redact, or generalize each sensitive item
   - Preserve enough context for the summary to remain useful
   - Maintain readability and coherence

3. **APPLY SANITIZATION:**
   - Replace email addresses with [EMAIL]
   - Replace phone numbers with [PHONE]
   - Replace account numbers with [ACCOUNT_NUM]
   - Replace names with generic identifiers if needed (e.g., "Customer A")
   - Generalize specific amounts or values if they're sensitive

4. **VERIFY COMPLETENESS:**
   - Double-check for any missed sensitive information
   - Ensure the sanitized version is still actionable
   - Confirm no data leakage through context

**Output Format:**
Provide your response in the following JSON structure:
{{
  "reasoning_steps": {{
    "identified_sensitive_data": ["item1", "item2"],
    "sanitization_strategy": "...",
    "verification_notes": "..."
  }},
  "sanitized_summary": "The fully sanitized summary text",
  "sanitization_log": [
    {{"original": "john@example.com", "sanitized": "[EMAIL]", "type": "email"}},
    {{"original": "+1-555-1234", "sanitized": "[PHONE]", "type": "phone"}}
  ],
  "confidence_score": 0.98
}}

Think carefully and ensure complete sanitization while maintaining summary usefulness.
"""

AGENT_ASSIGNMENT_COT_PROMPT = """You are an expert AI assistant helping to assign cases to the most appropriate customer service agents.

**Case Summary:**
{case_summary}

**Priority:** {priority}

**Required Skills/Expertise:**
{required_skills}

**Available Agents:**
{available_agents}

**Assignment Instructions:**
Follow this chain-of-thought reasoning process:

1. **ANALYZE CASE REQUIREMENTS:**
   - What technical skills or domain knowledge is needed?
   - What is the complexity level?
   - Are there any special requirements (language, timezone, etc.)?

2. **EVALUATE AGENT CAPABILITIES:**
   - Which agents have the required skills?
   - What is their current workload?
   - What is their historical performance on similar cases?

3. **MATCH AND RANK:**
   - Score each agent based on skill match, availability, and performance
   - Consider workload balancing
   - Factor in any special constraints

4. **MAKE RECOMMENDATION:**
   - Select the best-fit agent(s)
   - Provide reasoning for the selection
   - Suggest backup options if primary choice is unavailable

**Output Format:**
Provide your response in the following JSON structure:
{{
  "reasoning_steps": {{
    "case_requirements": "...",
    "agent_evaluation": "...",
    "matching_logic": "..."
  }},
  "recommended_agent": {{
    "agent_id": "...",
    "agent_name": "...",
    "match_score": 0.95,
    "reasoning": "..."
  }},
  "backup_agents": [
    {{"agent_id": "...", "agent_name": "...", "match_score": 0.85}}
  ],
  "confidence_score": 0.92
}}

Think step-by-step to ensure optimal agent assignment.
"""
