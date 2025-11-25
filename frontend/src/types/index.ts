/**
 * TypeScript type definitions
 */

export interface CaseData {
  case_id: string;
  subject: string;
  description: string;
  priority: string;
  status: string;
  created_date: string;
  account_id?: string;
  contact_id?: string;
}

export interface CaseAnalysisRequest {
  case_id: string;
  include_related_objects?: boolean;
}

export interface ReasoningSteps {
  problem_understanding?: string;
  data_analysis?: string;
  key_insights?: string;
  action_planning?: string;
}

export interface CaseAnalysisResponse {
  case_id: string;
  reasoning_steps?: ReasoningSteps;
  summary: string;
  next_actions: string[];
  priority_level: string;
  estimated_resolution_time?: string;
  required_teams: string[];
  confidence_score: number;
  raw_summary: string;
  sanitized_summary: string;
  accuracy_percentage: number;
}

export interface AgentInfo {
  agent_id: string;
  agent_name: string;
  email: string;
  skills: string[];
  current_workload: number;
  availability_status: string;
}

export interface ChatMessage {
  message_id?: string;
  sender: string;
  content: string;
  timestamp: string;
  case_id?: string;
  metadata?: Record<string, any>;
  type?: string;
  sender_role?: string;
  sender_id?: string;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
  role: string;
}

export interface User {
  id: string;
  name: string;
  role: 'user' | 'agent';
  email?: string;
}
