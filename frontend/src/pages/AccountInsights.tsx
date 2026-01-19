/**
 * Account Insights Page - AI-powered account activity analysis
 */
import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { apiService } from '@/services/api';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { DateRangeSelector } from '@/components/DateRangeSelector';
import { FormatSelector } from '@/components/FormatSelector';
import { InsightsDisplay } from '@/components/InsightsDisplay';
import { useNavigate } from 'react-router-dom';
import type { SummaryFormat, AccountSearchResponse, AccountInsightsResponse } from '@/types';

export const AccountInsights: React.FC = () => {
    const navigate = useNavigate();

    // Form state
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedAccount, setSelectedAccount] = useState<AccountSearchResponse | null>(null);
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');
    const [selectedFormats, setSelectedFormats] = useState<SummaryFormat[]>(['pointers', 'tables']);

    // Search account mutation
    const searchMutation = useMutation({
        mutationFn: (identifier: string) => apiService.searchAccount(identifier),
        onSuccess: (data) => {
            if (data.found) {
                setSelectedAccount(data);
            }
        },
    });

    // Get insights mutation
    const insightsMutation = useMutation({
        mutationFn: () => {
            if (!selectedAccount?.account_id) {
                throw new Error('No account selected');
            }
            return apiService.getAccountInsights(
                selectedAccount.account_id,
                startDate,
                endDate,
                selectedFormats
            );
        },
    });

    const handleSearch = () => {
        if (searchQuery.trim()) {
            setSelectedAccount(null);
            insightsMutation.reset();
            searchMutation.mutate(searchQuery.trim());
        }
    };

    const handleGenerateInsights = () => {
        if (selectedAccount?.account_id && startDate && endDate) {
            insightsMutation.mutate();
        }
    };

    const handleDateChange = (start: string, end: string) => {
        setStartDate(start);
        setEndDate(end);
    };

    const handleClearAccount = () => {
        setSelectedAccount(null);
        setSearchQuery('');
        insightsMutation.reset();
    };

    const isLoading = searchMutation.isPending || insightsMutation.isPending;

    const getLoadingMessage = () => {
        if (searchMutation.isPending) return 'Searching for account...';
        if (insightsMutation.isPending) return 'Generating insights with AI (this may take a moment for large datasets)...';
        return 'Loading...';
    };

    const insights = insightsMutation.data as AccountInsightsResponse | undefined;

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
                {/* Header with Navigation */}
                <header className="mb-8">
                    <div className="flex justify-between items-center">
                        <div>
                            <h1 className="text-3xl font-bold text-gray-900">Account Activity Insights</h1>
                            <p className="text-gray-600 mt-2">
                                AI-powered analysis of account activities and key insights
                            </p>
                        </div>
                        <button
                            onClick={() => navigate('/agent')}
                            className="px-4 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                        >
                            Back to Dashboard
                        </button>
                    </div>
                </header>

                {/* Search Section */}
                <div className="bg-white rounded-lg shadow p-6 mb-6">
                    <h2 className="text-xl font-semibold mb-4">Find Account</h2>
                    <div className="flex gap-4">
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                            placeholder="Enter Account ID or Account Name"
                            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                            disabled={isLoading}
                        />
                        <button
                            onClick={handleSearch}
                            disabled={isLoading || !searchQuery.trim()}
                            className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                        >
                            Search
                        </button>
                    </div>

                    {/* Search Error */}
                    {searchMutation.isError && (
                        <div className="mt-4 p-3 bg-red-50 text-red-800 rounded-lg">
                            Account not found. Please check the ID or name and try again.
                        </div>
                    )}
                </div>

                {/* Selected Account Card */}
                {selectedAccount && (
                    <div className="bg-white rounded-lg shadow p-6 mb-6">
                        <div className="flex justify-between items-start mb-4">
                            <h2 className="text-xl font-semibold">Selected Account</h2>
                            <button
                                onClick={handleClearAccount}
                                className="text-sm text-gray-500 hover:text-gray-700"
                            >
                                Clear
                            </button>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div>
                                <p className="text-sm text-gray-500">Account Name</p>
                                <p className="font-semibold text-gray-900">{selectedAccount.account_name}</p>
                            </div>
                            <div>
                                <p className="text-sm text-gray-500">Type</p>
                                <p className="font-medium text-gray-700">{selectedAccount.account_type || 'N/A'}</p>
                            </div>
                            <div>
                                <p className="text-sm text-gray-500">Industry</p>
                                <p className="font-medium text-gray-700">{selectedAccount.industry || 'N/A'}</p>
                            </div>
                            <div>
                                <p className="text-sm text-gray-500">Location</p>
                                <p className="font-medium text-gray-700">
                                    {[selectedAccount.billing_city, selectedAccount.billing_state, selectedAccount.billing_country]
                                        .filter(Boolean)
                                        .join(', ') || 'N/A'}
                                </p>
                            </div>
                            <div>
                                <p className="text-sm text-gray-500">Owner</p>
                                <p className="font-medium text-gray-700">{selectedAccount.owner_name || 'N/A'}</p>
                            </div>
                            <div>
                                <p className="text-sm text-gray-500">Phone</p>
                                <p className="font-medium text-gray-700">{selectedAccount.phone || 'N/A'}</p>
                            </div>
                        </div>
                    </div>
                )}

                {/* Insights Configuration */}
                {selectedAccount && (
                    <div className="bg-white rounded-lg shadow p-6 mb-6">
                        <h2 className="text-xl font-semibold mb-6">Configure Insights</h2>

                        <div className="space-y-6">
                            {/* Date Range Selector */}
                            <DateRangeSelector
                                onDateChange={handleDateChange}
                                defaultMonths={3}
                            />

                            {/* Format Selector */}
                            <FormatSelector
                                selectedFormats={selectedFormats}
                                onFormatChange={setSelectedFormats}
                            />

                            {/* Generate Button */}
                            <div className="pt-4 border-t border-gray-200">
                                <button
                                    onClick={handleGenerateInsights}
                                    disabled={isLoading || !startDate || !endDate || selectedFormats.length === 0}
                                    className="w-full px-6 py-3 bg-primary-600 text-white text-lg font-medium rounded-lg hover:bg-primary-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                                >
                                    Generate Insights
                                </button>
                                <p className="mt-2 text-sm text-gray-500 text-center">
                                    Analyzing activities from {startDate || '...'} to {endDate || '...'}
                                </p>
                            </div>
                        </div>
                    </div>
                )}

                {/* Insights Error */}
                {insightsMutation.isError && (
                    <div className="bg-red-50 border border-red-200 text-red-800 rounded-lg p-4 mb-6">
                        Error generating insights. Please try again.
                    </div>
                )}

                {/* Insights Results */}
                {insights && (
                    <div className="space-y-6">
                        {/* Processing Info */}
                        <div className="bg-white rounded-lg shadow p-4">
                            <div className="flex flex-wrap gap-4 text-sm">
                                <div className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full">
                                    Total Activities: {insights.total_activities}
                                </div>
                                <div className="px-3 py-1 bg-green-100 text-green-800 rounded-full">
                                    Tasks: {insights.processing_info.task_count}
                                </div>
                                <div className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full">
                                    Events: {insights.processing_info.event_count}
                                </div>
                                <div className="px-3 py-1 bg-amber-100 text-amber-800 rounded-full">
                                    Cases: {insights.processing_info.case_count}
                                </div>
                                {insights.processing_info.batches_processed > 1 && (
                                    <div className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full">
                                        Processed in {insights.processing_info.batches_processed} batches
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Insights Display */}
                        <InsightsDisplay
                            executiveSummary={insights.executive_summary}
                            sections={insights.sections}
                            charts={insights.charts}
                        />
                    </div>
                )}
            </div>
        </div>
    );
};
