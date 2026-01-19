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

export interface CaseQueryRequest {
  question: string;
}

export interface CaseQueryResponse {
  answer: string;
  sources: string[];
  confidence: number;
  case_id: string;
}

export interface CaseClosedResponse {
  is_closed: boolean;
  case_number: string;
  status: string;
  message: string;
  closed_date?: string;
}

// =====================================================
// Account Insights Types
// =====================================================

export type SummaryFormat = 'tables' | 'pointers' | 'charts';

export interface AccountSearchRequest {
  identifier: string;
}

export interface AccountSearchResponse {
  found: boolean;
  account_id?: string;
  account_name?: string;
  account_type?: string;
  industry?: string;
  website?: string;
  phone?: string;
  billing_city?: string;
  billing_state?: string;
  billing_country?: string;
  owner_name?: string;
  message?: string;
}

export interface DateRange {
  start_date: string;
  end_date: string;
}

export interface AccountInsightsRequest {
  start_date: string;
  end_date: string;
  formats: SummaryFormat[];
}

export interface InsightSection {
  title: string;
  format: SummaryFormat;
  content: string | string[] | Record<string, unknown>;
}

export interface ChartDataset {
  label?: string;
  data: number[];
  backgroundColor?: string | string[];
  borderColor?: string;
  fill?: boolean;
}

export interface ChartData {
  title: string;
  chart_type: 'bar' | 'line' | 'pie';
  labels: string[];
  datasets: ChartDataset[];
}

export interface TableData {
  headers: string[];
  rows: (string | number)[][];
}

export interface ProcessingInfo {
  batch_size: number;
  batches_processed: number;
  task_count: number;
  event_count: number;
  case_count: number;
}

export interface AccountInsightsResponse {
  account_id: string;
  account_name: string;
  date_range: DateRange;
  total_activities: number;
  processing_info: ProcessingInfo;
  sections: InsightSection[];
  charts?: ChartData[];
  executive_summary: string;
  generated_at: string;
}
