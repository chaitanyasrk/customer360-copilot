/**
 * Sales Rep Summary Component
 * Renders the multi-agent pipeline output with contact interactions,
 * case trends, key takeaways, and executive summary.
 */
import React, { useEffect, useRef } from 'react';
import Chart from 'chart.js/auto';
import type { SalesRepSummaryResponse, ContactInteraction, CaseTrendCategory } from '@/types';

interface SalesRepSummaryProps {
    data: SalesRepSummaryResponse;
}

// =====================================================
// Sub-components
// =====================================================

/** Contact card with glassmorphism styling */
const ContactCard: React.FC<{ contact: ContactInteraction; index: number }> = ({ contact, index }) => {
    const activityIcons: Record<string, string> = {
        'Call': '📞',
        'Email': '📧',
        'Meeting': '📅',
        'Task': '📋',
        'Event': '📅',
    };

    return (
        <div
            className="relative bg-white/80 backdrop-blur-sm border border-gray-200/60 rounded-xl p-5 hover:shadow-lg hover:border-primary-200 transition-all duration-300 group"
            style={{ animationDelay: `${index * 80}ms` }}
        >
            {/* Header */}
            <div className="flex items-start gap-3 mb-3">
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center text-white font-semibold text-sm shadow-sm">
                    {contact.contact_name?.charAt(0)?.toUpperCase() || '?'}
                </div>
                <div className="flex-1 min-w-0">
                    <h4 className="font-semibold text-gray-900 truncate">{contact.contact_name}</h4>
                    {contact.contact_title && (
                        <p className="text-sm text-gray-500 truncate">{contact.contact_title}</p>
                    )}
                </div>
                <div className="flex-shrink-0 bg-primary-50 text-primary-700 text-xs font-semibold px-2.5 py-1 rounded-full">
                    {contact.interaction_count} interaction{contact.interaction_count !== 1 ? 's' : ''}
                </div>
            </div>

            {/* Email */}
            {contact.contact_email && (
                <p className="text-xs text-gray-400 mb-3 truncate">{contact.contact_email}</p>
            )}

            {/* Activity types */}
            {contact.activity_types.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mb-3">
                    {contact.activity_types.map((type, i) => (
                        <span
                            key={i}
                            className="inline-flex items-center gap-1 text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded-md"
                        >
                            <span>{activityIcons[type] || '📌'}</span>
                            {type}
                        </span>
                    ))}
                </div>
            )}

            {/* Topics */}
            {contact.topics.length > 0 && (
                <div className="mb-3">
                    <p className="text-xs font-medium text-gray-500 mb-1.5">Topics Discussed</p>
                    <div className="flex flex-wrap gap-1.5">
                        {contact.topics.slice(0, 5).map((topic, i) => (
                            <span
                                key={i}
                                className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded-md border border-blue-100 truncate max-w-[200px]"
                                title={topic}
                            >
                                {topic}
                            </span>
                        ))}
                        {contact.topics.length > 5 && (
                            <span className="text-xs px-2 py-0.5 bg-gray-50 text-gray-500 rounded-md">
                                +{contact.topics.length - 5} more
                            </span>
                        )}
                    </div>
                </div>
            )}

            {/* Last interaction */}
            {contact.last_interaction_date && (
                <p className="text-xs text-gray-400">
                    Last contact: {new Date(contact.last_interaction_date).toLocaleDateString('en-US', {
                        month: 'short', day: 'numeric', year: 'numeric'
                    })}
                </p>
            )}
        </div>
    );
};

/** Case trend category card */
const TrendCard: React.FC<{ trend: CaseTrendCategory; maxCount: number; index: number }> = ({
    trend, maxCount, index,
}) => {
    const trendIcons: Record<string, { icon: string; color: string }> = {
        rising: { icon: '↗', color: 'text-red-500' },
        stable: { icon: '→', color: 'text-gray-500' },
        declining: { icon: '↘', color: 'text-green-500' },
    };

    const trendInfo = trendIcons[trend.trend] || trendIcons.stable;
    const barWidth = maxCount > 0 ? (trend.count / maxCount) * 100 : 0;

    // Color palette for categories
    const colors = [
        { bg: 'bg-blue-500', light: 'bg-blue-50', text: 'text-blue-700' },
        { bg: 'bg-amber-500', light: 'bg-amber-50', text: 'text-amber-700' },
        { bg: 'bg-purple-500', light: 'bg-purple-50', text: 'text-purple-700' },
        { bg: 'bg-rose-500', light: 'bg-rose-50', text: 'text-rose-700' },
        { bg: 'bg-teal-500', light: 'bg-teal-50', text: 'text-teal-700' },
        { bg: 'bg-indigo-500', light: 'bg-indigo-50', text: 'text-indigo-700' },
    ];
    const color = colors[index % colors.length];

    return (
        <div className="group" style={{ animationDelay: `${index * 60}ms` }}>
            <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                    <span className={`text-sm font-medium text-gray-900`}>{trend.category}</span>
                    <span className={`text-sm font-bold ${trendInfo.color}`}>{trendInfo.icon}</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-gray-700">{trend.count}</span>
                    <span className="text-xs text-gray-400">({trend.percentage.toFixed(1)}%)</span>
                </div>
            </div>

            {/* Progress bar */}
            <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden mb-2">
                <div
                    className={`h-full ${color.bg} rounded-full transition-all duration-700 ease-out`}
                    style={{ width: `${barWidth}%` }}
                />
            </div>

            {/* Recent examples (shown on hover) */}
            {trend.recent_examples.length > 0 && (
                <div className="overflow-hidden max-h-0 group-hover:max-h-24 transition-all duration-300 ease-in-out">
                    <div className={`${color.light} rounded-lg p-2 mt-1`}>
                        <p className="text-xs font-medium text-gray-500 mb-1">Recent examples:</p>
                        {trend.recent_examples.slice(0, 3).map((example, i) => (
                            <p key={i} className={`text-xs ${color.text} truncate`} title={example}>
                                • {example}
                            </p>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

/** Case trends donut chart */
const TrendsChart: React.FC<{ trends: CaseTrendCategory[] }> = ({ trends }) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const chartRef = useRef<Chart | null>(null);

    useEffect(() => {
        if (!canvasRef.current || trends.length === 0) return;

        if (chartRef.current) {
            chartRef.current.destroy();
        }

        const ctx = canvasRef.current.getContext('2d');
        if (!ctx) return;

        const colors = [
            'rgba(59, 130, 246, 0.85)',
            'rgba(245, 158, 11, 0.85)',
            'rgba(139, 92, 246, 0.85)',
            'rgba(244, 63, 94, 0.85)',
            'rgba(20, 184, 166, 0.85)',
            'rgba(99, 102, 241, 0.85)',
            'rgba(236, 72, 153, 0.85)',
            'rgba(34, 197, 94, 0.85)',
        ];

        chartRef.current = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: trends.map(t => t.category),
                datasets: [{
                    data: trends.map(t => t.count),
                    backgroundColor: colors.slice(0, trends.length),
                    borderWidth: 2,
                    borderColor: '#fff',
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                cutout: '60%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 12,
                            usePointStyle: true,
                            pointStyleWidth: 8,
                            font: { size: 11 },
                        },
                    },
                },
            },
        });

        return () => {
            if (chartRef.current) {
                chartRef.current.destroy();
            }
        };
    }, [trends]);

    if (trends.length === 0) return null;

    return (
        <div className="w-full max-w-xs mx-auto">
            <canvas ref={canvasRef} />
        </div>
    );
};

// =====================================================
// Main Component
// =====================================================

export const SalesRepSummary: React.FC<SalesRepSummaryProps> = ({ data }) => {
    return (
        <div className="space-y-6">
            {/* Executive Summary Banner */}
            <div className="bg-gradient-to-r from-primary-600 via-primary-700 to-blue-700 rounded-xl p-6 shadow-lg">
                <h3 className="text-lg font-semibold text-white/90 mb-2">Executive Summary</h3>
                <p className="text-white/95 leading-relaxed text-sm">{data.executive_summary}</p>
            </div>

            {/* Stats Bar */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
                    <p className="text-2xl font-bold text-primary-600">{data.total_activities}</p>
                    <p className="text-xs text-gray-500 mt-1">Activities</p>
                </div>
                <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
                    <p className="text-2xl font-bold text-amber-600">{data.total_cases}</p>
                    <p className="text-xs text-gray-500 mt-1">Cases</p>
                </div>
                <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
                    <p className="text-2xl font-bold text-green-600">{data.contact_interactions?.length || 0}</p>
                    <p className="text-xs text-gray-500 mt-1">Contacts Engaged</p>
                </div>
                <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
                    <p className="text-2xl font-bold text-purple-600">{data.case_trends?.length || 0}</p>
                    <p className="text-xs text-gray-500 mt-1">Case Categories</p>
                </div>
            </div>

            {/* Contact Interactions */}
            {data.contact_interactions && data.contact_interactions.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-200 p-6">
                    <div className="flex items-center gap-2 mb-5">
                        <div className="w-1 h-6 bg-primary-500 rounded-full" />
                        <h3 className="text-lg font-semibold text-gray-900">Contact Interactions</h3>
                        <span className="text-sm text-gray-400 ml-auto">
                            {data.contact_interactions.length} contact{data.contact_interactions.length !== 1 ? 's' : ''}
                        </span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {data.contact_interactions.map((contact, idx) => (
                            <ContactCard key={idx} contact={contact} index={idx} />
                        ))}
                    </div>
                </div>
            )}

            {/* Case Trends */}
            {data.case_trends && data.case_trends.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-200 p-6">
                    <div className="flex items-center gap-2 mb-5">
                        <div className="w-1 h-6 bg-amber-500 rounded-full" />
                        <h3 className="text-lg font-semibold text-gray-900">Case Trends</h3>
                        <span className="text-sm text-gray-400 ml-auto">
                            {data.total_cases} total case{data.total_cases !== 1 ? 's' : ''}
                        </span>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
                        {/* Chart */}
                        <div className="lg:col-span-2">
                            <TrendsChart trends={data.case_trends} />
                        </div>

                        {/* Category breakdown */}
                        <div className="lg:col-span-3 space-y-4">
                            {data.case_trends.map((trend, idx) => (
                                <TrendCard
                                    key={idx}
                                    trend={trend}
                                    maxCount={Math.max(...data.case_trends.map(t => t.count))}
                                    index={idx}
                                />
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* Key Takeaways */}
            {data.key_takeaways && data.key_takeaways.length > 0 && (
                <div className="bg-gradient-to-br from-gray-50 to-blue-50/50 rounded-xl border border-gray-200 p-6">
                    <div className="flex items-center gap-2 mb-4">
                        <div className="w-1 h-6 bg-green-500 rounded-full" />
                        <h3 className="text-lg font-semibold text-gray-900">Key Takeaways</h3>
                    </div>
                    <div className="space-y-3">
                        {data.key_takeaways.map((takeaway, idx) => (
                            <div key={idx} className="flex items-start gap-3">
                                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-green-100 text-green-700 flex items-center justify-center text-xs font-bold mt-0.5">
                                    {idx + 1}
                                </span>
                                <p className="text-sm text-gray-700 leading-relaxed">{takeaway}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Pipeline Info (subtle footer) */}
            {data.pipeline_info && (
                <div className="flex flex-wrap items-center gap-3 text-xs text-gray-400 px-1">
                    <span>Metadata: {data.pipeline_info.metadata_source || 'N/A'}</span>
                    <span>•</span>
                    <span>Queries: {data.pipeline_info.queries_generated || 0}</span>
                    <span>•</span>
                    <span>Activities: {data.pipeline_info.activities_fetched || 0}</span>
                    <span>•</span>
                    <span>Contacts: {data.pipeline_info.contacts_resolved || 0}</span>
                    {data.pipeline_info.total_elapsed_seconds && (
                        <>
                            <span>•</span>
                            <span>Processing: {data.pipeline_info.total_elapsed_seconds.toFixed(1)}s</span>
                        </>
                    )}
                    {data.pipeline_info.query_errors && data.pipeline_info.query_errors.length > 0 && (
                        <>
                            <span>•</span>
                            <span className="text-amber-500">
                                {data.pipeline_info.query_errors.length} query warning(s)
                            </span>
                        </>
                    )}
                </div>
            )}
        </div>
    );
};
