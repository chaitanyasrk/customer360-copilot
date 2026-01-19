/**
 * API service for backend communication
 */
import axios, { AxiosInstance } from 'axios';
import type {
  CaseAnalysisRequest,
  CaseAnalysisResponse,
  AgentInfo,
  AuthToken,
  AccountSearchResponse,
  AccountInsightsResponse,
  SummaryFormat,
} from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add request interceptor to include auth token
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('auth_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Add response interceptor to handle 401 Unauthorized
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Clear token and redirect to login
          localStorage.removeItem('auth_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Authentication
  async login(username: string, password: string, role: string = 'agent'): Promise<AuthToken> {
    const response = await this.client.post<AuthToken>('/auth/token', null, {
      params: { username, password, role },
    });
    return response.data;
  }

  // Case Analysis
  async analyzeCase(request: CaseAnalysisRequest): Promise<CaseAnalysisResponse> {
    const response = await this.client.post<CaseAnalysisResponse>('/cases/analyze', request);
    return response.data;
  }

  // Get case details
  async getCaseDetails(caseId: string) {
    const response = await this.client.get(`/cases/${caseId}`);
    return response.data;
  }

  // Get available agents (optionally for a specific case)
  async getAvailableAgents(caseNumber?: string): Promise<AgentInfo[]> {
    const params = caseNumber ? { case_number: caseNumber } : {};
    const response = await this.client.get<AgentInfo[]>('/agents/available', { params });
    return response.data;
  }

  // Notify agents
  async notifyAgents(caseId: string, agentIds: string[], summary: string) {
    const response = await this.client.post(`/cases/${caseId}/notify-agents`, {
      agent_ids: agentIds,
      summary,
    });
    return response.data;
  }

  // Save case summary to Salesforce custom object
  async saveCaseSummary(caseId: string, summary: string, additionalData?: Record<string, any>) {
    const response = await this.client.post(`/cases/${caseId}/save-summary`, {
      summary,
      additional_data: additionalData,
    });
    return response.data;
  }

  // Health check
  async healthCheck() {
    const response = await this.client.get('/health');
    return response.data;
  }

  // Ask a question about a case
  async queryCaseDetails(caseId: string, question: string) {
    const response = await this.client.post(`/cases/${caseId}/query`, {
      question,
    });
    return response.data;
  }

  // =====================================================
  // Account Insights Methods
  // =====================================================

  // Search for an account by ID or Name
  async searchAccount(identifier: string): Promise<AccountSearchResponse> {
    const response = await this.client.post<AccountSearchResponse>('/accounts/search', {
      identifier,
    });
    return response.data;
  }

  // Get account activity insights
  async getAccountInsights(
    accountId: string,
    startDate: string,
    endDate: string,
    formats: SummaryFormat[]
  ): Promise<AccountInsightsResponse> {
    const response = await this.client.post<AccountInsightsResponse>(
      `/accounts/${accountId}/insights`,
      {
        start_date: startDate,
        end_date: endDate,
        formats,
      }
    );
    return response.data;
  }
}

export const apiService = new ApiService();
