/**
 * API service for backend communication
 */
import axios, { AxiosInstance } from 'axios';
import type {
  CaseAnalysisRequest,
  CaseAnalysisResponse,
  AgentInfo,
  AuthToken,
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

  // Get available agents
  async getAvailableAgents(): Promise<AgentInfo[]> {
    const response = await this.client.get<AgentInfo[]>('/agents/available');
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

  // Health check
  async healthCheck() {
    const response = await this.client.get('/health');
    return response.data;
  }
}

export const apiService = new ApiService();
