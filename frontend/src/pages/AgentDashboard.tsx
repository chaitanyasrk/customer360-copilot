/**
 * Agent Dashboard - Main interface for customer service agents
 */
import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiService } from '@/services/api';
import { AlertCircle, CheckCircle, Clock, Users } from 'lucide-react';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { CaseChat } from '@/components/CaseChat';
import type { CaseAnalysisResponse, CaseClosedResponse } from '@/types';


export const AgentDashboard: React.FC = () => {
  const [caseId, setCaseId] = useState('');
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const [analyzedCaseNumber, setAnalyzedCaseNumber] = useState<string | null>(null);

  // Fetch available agents (with case number when available)
  const { data: agents } = useQuery({
    queryKey: ['agents', analyzedCaseNumber],
    queryFn: () => apiService.getAvailableAgents(analyzedCaseNumber || undefined),
    enabled: true,
  });


  // Analyze case mutation - can return either analysis or closed case response
  const analyzeMutation = useMutation({
    mutationFn: (caseId: string) =>
      apiService.analyzeCase({ case_id: caseId, include_related_objects: true }),
  });

  // Notify agents mutation
  const notifyMutation = useMutation({
    mutationFn: ({ caseId, agentIds, summary }: { caseId: string; agentIds: string[]; summary: string }) =>
      apiService.notifyAgents(caseId, agentIds, summary),
  });

  // Save summary mutation
  const saveSummaryMutation = useMutation({
    mutationFn: ({ caseId, summary }: { caseId: string; summary: string }) =>
      apiService.saveCaseSummary(caseId, summary),
  });

  const handleAnalyze = () => {
    if (caseId.trim()) {
      setAnalyzedCaseNumber(caseId.trim());
      analyzeMutation.mutate(caseId);
    }
  };

  const handleNotifyAgents = () => {
    if (analyzeMutation.data && !isCaseClosed && selectedAgents.length > 0) {
      const data = analyzeMutation.data as CaseAnalysisResponse;
      notifyMutation.mutate({
        caseId: data.case_id,
        agentIds: selectedAgents,
        summary: data.sanitized_summary,
      });
    }
  };

  const handleSaveSummary = () => {
    if (analyzeMutation.data && !isCaseClosed) {
      const data = analyzeMutation.data as CaseAnalysisResponse;
      saveSummaryMutation.mutate({
        caseId: data.case_id,
        summary: data.sanitized_summary,
      });
    }
  };

  // Check if response indicates a closed case
  const isCaseClosed = analyzeMutation.data && 'is_closed' in analyzeMutation.data && (analyzeMutation.data as unknown as CaseClosedResponse).is_closed;
  const closedCaseData = isCaseClosed ? (analyzeMutation.data as unknown as CaseClosedResponse) : null;

  // Only set analysis if it has the expected properties (not a closed case response)
  const rawData = analyzeMutation.data as CaseAnalysisResponse | undefined;
  const analysis: CaseAnalysisResponse | undefined = (!isCaseClosed && rawData && 'accuracy_percentage' in rawData) ? rawData : undefined;



  // Determine loading message
  const getLoadingMessage = () => {
    if (analyzeMutation.isPending) return 'Analyzing case with AI...';
    if (saveSummaryMutation.isPending) return 'Saving summary to Salesforce...';
    if (notifyMutation.isPending) return 'Sending notifications...';
    return 'Loading...';
  };

  const isLoading = analyzeMutation.isPending || saveSummaryMutation.isPending || notifyMutation.isPending;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Loading Overlay */}
      {isLoading && (
        <LoadingSpinner
          fullscreen
          size="lg"
          message={getLoadingMessage()}
        />
      )}

      <div className="max-w-7xl mx-auto px-4 py-8">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Customer 360 Copilot</h1>
          <p className="text-gray-600 mt-2">AI-powered case analysis and management</p>
        </header>

        {/* Case Input Section */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Analyze Case</h2>
          <div className="flex gap-4">
            <input
              type="text"
              value={caseId}
              onChange={(e) => setCaseId(e.target.value)}
              placeholder="Enter Case Number (e.g., 00001234)"
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
            <button
              onClick={handleAnalyze}
              disabled={analyzeMutation.isPending}
              className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {analyzeMutation.isPending ? 'Analyzing...' : 'Analyze'}
            </button>
          </div>
        </div>

        {/* Closed Case Message */}
        {isCaseClosed && closedCaseData && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-6 mb-6">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0">
                <AlertCircle className="w-8 h-8 text-amber-600" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-amber-800 mb-2">
                  Case Closed
                </h3>
                <p className="text-amber-700 mb-2">
                  {closedCaseData.message || 'This case is closed. Analysis is not available for closed cases.'}
                </p>
                <div className="text-sm text-amber-600 space-y-1">
                  <p><strong>Case Number:</strong> {closedCaseData.case_number}</p>
                  <p><strong>Status:</strong> {closedCaseData.status}</p>
                  {closedCaseData.closed_date && (
                    <p><strong>Closed Date:</strong> {new Date(closedCaseData.closed_date).toLocaleDateString()}</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Analysis Results */}
        {analysis && (
          <div className="space-y-6">
            {/* Metrics Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <MetricCard
                icon={<CheckCircle className="w-6 h-6 text-green-600" />}
                label="Accuracy"
                value={`${analysis.accuracy_percentage.toFixed(1)}%`}
                color="green"
              />
              <MetricCard
                icon={<AlertCircle className="w-6 h-6 text-yellow-600" />}
                label="Priority"
                value={analysis.priority_level}
                color="yellow"
              />
              <MetricCard
                icon={<Clock className="w-6 h-6 text-blue-600" />}
                label="Est. Resolution"
                value={analysis.estimated_resolution_time || 'N/A'}
                color="blue"
              />
            </div>

            {/* Summary Section */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">Case Summary</h3>
              <div className="prose max-w-none">
                <p className="text-gray-700">{analysis.sanitized_summary}</p>
              </div>
              <div className="mt-4 flex items-center gap-4">
                <button
                  onClick={handleSaveSummary}
                  disabled={saveSummaryMutation.isPending}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
                  </svg>
                  Save to Salesforce
                </button>
                {saveSummaryMutation.isSuccess && (
                  <span className="text-green-600 flex items-center gap-1">
                    <CheckCircle className="w-4 h-4" />
                    Summary saved successfully!
                  </span>
                )}
                {saveSummaryMutation.isError && (
                  <span className="text-red-600 flex items-center gap-1">
                    <AlertCircle className="w-4 h-4" />
                    Failed to save summary
                  </span>
                )}
              </div>
            </div>

            {/* Next Actions */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">Recommended Next Actions</h3>
              <ol className="list-decimal list-inside space-y-2">
                {analysis.next_actions.map((action, idx) => (
                  <li key={idx} className="text-gray-700">
                    {action}
                  </li>
                ))}
              </ol>
            </div>

            {/* Required Teams */}
            {analysis.required_teams.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <Users className="w-5 h-5" />
                  Required Teams
                </h3>
                <div className="flex flex-wrap gap-2">
                  {analysis.required_teams.map((team, idx) => (
                    <span
                      key={idx}
                      className="px-3 py-1 bg-primary-100 text-primary-800 rounded-full text-sm"
                    >
                      {team}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Agent Notification */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">Notify Agents</h3>
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {agents?.map((agent) => (
                    <label
                      key={agent.agent_id}
                      className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedAgents.includes(agent.agent_id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedAgents([...selectedAgents, agent.agent_id]);
                          } else {
                            setSelectedAgents(selectedAgents.filter((id) => id !== agent.agent_id));
                          }
                        }}
                        className="w-4 h-4 text-primary-600"
                      />
                      <div className="flex-1">
                        <div className="font-medium">{agent.agent_name}</div>
                        <div className="text-sm text-gray-500">
                          {agent.skills.slice(0, 2).join(', ')}
                        </div>
                      </div>
                      <div className="text-sm text-gray-500">Load: {agent.current_workload}</div>
                    </label>
                  ))}
                </div>
                <button
                  onClick={handleNotifyAgents}
                  disabled={selectedAgents.length === 0 || notifyMutation.isPending}
                  className="w-full px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                >
                  {notifyMutation.isPending
                    ? 'Sending...'
                    : `Notify ${selectedAgents.length} Agent(s)`}
                </button>
                {notifyMutation.isSuccess && (
                  <div className="p-3 bg-green-50 text-green-800 rounded-lg">
                    ✓ Notification sent successfully!
                  </div>
                )}
              </div>
            </div>

            {/* Case Q&A Chat */}
            <CaseChat caseId={analysis.case_id} />
          </div>
        )}

        {/* Error Display */}
        {analyzeMutation.isError && (
          <div className="bg-red-50 border border-red-200 text-red-800 rounded-lg p-4">
            <strong>Error:</strong> {(analyzeMutation.error as Error).message}
          </div>
        )}
      </div>
    </div>
  );
};

interface MetricCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: 'green' | 'yellow' | 'blue';
}

const MetricCard: React.FC<MetricCardProps> = ({ icon, label, value, color }) => {
  const colorClasses = {
    green: 'bg-green-50 border-green-200',
    yellow: 'bg-yellow-50 border-yellow-200',
    blue: 'bg-blue-50 border-blue-200',
  };

  return (
    <div className={`${colorClasses[color]} border rounded-lg p-4`}>
      <div className="flex items-center gap-3">
        {icon}
        <div>
          <div className="text-sm text-gray-600">{label}</div>
          <div className="text-xl font-semibold">{value}</div>
        </div>
      </div>
    </div>
  );
};
