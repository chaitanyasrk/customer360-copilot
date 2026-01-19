/**
 * Insights Display Component
 * Renders the generated insights in various formats (tables, bullet points, charts)
 */
import React, { useEffect, useRef } from 'react';
import Chart from 'chart.js/auto';
import type { InsightSection, ChartData, TableData } from '@/types';

interface InsightsDisplayProps {
    executiveSummary: string;
    sections: InsightSection[];
    charts?: ChartData[];
}

// Table renderer component
const TableRenderer: React.FC<{ data: TableData }> = ({ data }) => {
    if (!data.headers || !data.rows) {
        return null;
    }

    return (
        <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                    <tr>
                        {data.headers.map((header, idx) => (
                            <th
                                key={idx}
                                className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider"
                            >
                                {header}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                    {data.rows.map((row, rowIdx) => (
                        <tr key={rowIdx} className={rowIdx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                            {row.map((cell, cellIdx) => (
                                <td key={cellIdx} className="px-4 py-3 text-sm text-gray-900">
                                    {cell}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

// Bullet points renderer
const PointersRenderer: React.FC<{ content: string | string[] }> = ({ content }) => {
    const items = Array.isArray(content) ? content : [content];

    return (
        <ul className="space-y-2">
            {items.map((item, idx) => (
                <li key={idx} className="flex items-start gap-2">
                    <span className="flex-shrink-0 w-1.5 h-1.5 mt-2 rounded-full bg-primary-500" />
                    <span className="text-gray-700">{item}</span>
                </li>
            ))}
        </ul>
    );
};

// Chart renderer component
const ChartRenderer: React.FC<{ data: ChartData }> = ({ data }) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const chartRef = useRef<Chart | null>(null);

    useEffect(() => {
        if (!canvasRef.current) return;

        // Destroy existing chart
        if (chartRef.current) {
            chartRef.current.destroy();
        }

        const ctx = canvasRef.current.getContext('2d');
        if (!ctx) return;

        chartRef.current = new Chart(ctx, {
            type: data.chart_type,
            data: {
                labels: data.labels,
                datasets: data.datasets.map((dataset) => ({
                    ...dataset,
                    backgroundColor: dataset.backgroundColor || [
                        'rgba(59, 130, 246, 0.8)',
                        'rgba(16, 185, 129, 0.8)',
                        'rgba(245, 158, 11, 0.8)',
                        'rgba(239, 68, 68, 0.8)',
                        'rgba(139, 92, 246, 0.8)',
                    ],
                    borderColor: dataset.borderColor || 'rgba(59, 130, 246, 1)',
                    borderWidth: 1,
                })),
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: data.chart_type !== 'bar',
                        position: 'bottom',
                    },
                    title: {
                        display: false,
                    },
                },
                scales: data.chart_type !== 'pie' ? {
                    y: {
                        beginAtZero: true,
                    },
                } : undefined,
            },
        });

        return () => {
            if (chartRef.current) {
                chartRef.current.destroy();
            }
        };
    }, [data]);

    return (
        <div className="h-64">
            <canvas ref={canvasRef} />
        </div>
    );
};

// Section renderer
const SectionRenderer: React.FC<{ section: InsightSection }> = ({ section }) => {
    const renderContent = () => {
        switch (section.format) {
            case 'tables':
                if (typeof section.content === 'object' && !Array.isArray(section.content)) {
                    // Handle table data object with multiple tables
                    const tableEntries = Object.entries(section.content as Record<string, unknown>);
                    return (
                        <div className="space-y-4">
                            {tableEntries.map(([key, value]) => {
                                const tableData = value as TableData;
                                if (tableData && tableData.headers && tableData.rows) {
                                    return (
                                        <div key={key}>
                                            <h5 className="text-sm font-medium text-gray-600 mb-2 capitalize">
                                                {key.replace(/_/g, ' ')}
                                            </h5>
                                            <TableRenderer data={tableData} />
                                        </div>
                                    );
                                }
                                return null;
                            })}
                        </div>
                    );
                }
                return null;

            case 'pointers':
                return <PointersRenderer content={section.content as string | string[]} />;

            case 'charts':
                // Charts are rendered separately
                return null;

            default:
                if (typeof section.content === 'string') {
                    return <p className="text-gray-700">{section.content}</p>;
                }
                return null;
        }
    };

    return (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h4 className="text-lg font-semibold text-gray-900 mb-4">{section.title}</h4>
            {renderContent()}
        </div>
    );
};

export const InsightsDisplay: React.FC<InsightsDisplayProps> = ({
    executiveSummary,
    sections,
    charts,
}) => {
    return (
        <div className="space-y-6">
            {/* Executive Summary */}
            <div className="bg-gradient-to-r from-primary-50 to-blue-50 rounded-lg p-6 border border-primary-100">
                <h3 className="text-lg font-semibold text-gray-900 mb-3">Executive Summary</h3>
                <p className="text-gray-700 leading-relaxed">{executiveSummary}</p>
            </div>

            {/* Sections */}
            {sections.map((section, idx) => (
                <SectionRenderer key={idx} section={section} />
            ))}

            {/* Charts */}
            {charts && charts.length > 0 && (
                <div className="bg-white rounded-lg border border-gray-200 p-6">
                    <h4 className="text-lg font-semibold text-gray-900 mb-4">Visual Analytics</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {charts.map((chart, idx) => (
                            <div key={idx} className="bg-gray-50 rounded-lg p-4">
                                <h5 className="text-sm font-medium text-gray-700 mb-3">{chart.title}</h5>
                                <ChartRenderer data={chart} />
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};
