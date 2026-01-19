/**
 * Format Selector Component
 * Allows users to select output formats for insights
 */
import React from 'react';
import type { SummaryFormat } from '@/types';

interface FormatSelectorProps {
    selectedFormats: SummaryFormat[];
    onFormatChange: (formats: SummaryFormat[]) => void;
}

const formatOptions: { value: SummaryFormat; label: string; description: string }[] = [
    { value: 'pointers', label: 'Bullet Points', description: 'Key insights as bullet points' },
    { value: 'tables', label: 'Tables', description: 'Structured data tables' },
    { value: 'charts', label: 'Charts', description: 'Visual charts and graphs' },
];

export const FormatSelector: React.FC<FormatSelectorProps> = ({
    selectedFormats,
    onFormatChange,
}) => {
    const handleToggle = (format: SummaryFormat) => {
        if (selectedFormats.includes(format)) {
            // Don't allow deselecting if it's the last one
            if (selectedFormats.length > 1) {
                onFormatChange(selectedFormats.filter((f) => f !== format));
            }
        } else {
            onFormatChange([...selectedFormats, format]);
        }
    };

    const handleSelectAll = () => {
        const allFormats: SummaryFormat[] = ['pointers', 'tables', 'charts'];
        onFormatChange(allFormats);
    };

    const isAllSelected = selectedFormats.length === formatOptions.length;

    return (
        <div className="space-y-3">
            <div className="flex justify-between items-center">
                <label className="block text-sm font-medium text-gray-700">Output Format</label>
                <button
                    type="button"
                    onClick={handleSelectAll}
                    className={`text-sm px-3 py-1 rounded-lg transition-colors ${isAllSelected
                            ? 'bg-primary-100 text-primary-700'
                            : 'text-primary-600 hover:bg-primary-50'
                        }`}
                >
                    {isAllSelected ? 'All Selected' : 'Select All'}
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {formatOptions.map((option) => {
                    const isSelected = selectedFormats.includes(option.value);
                    return (
                        <button
                            key={option.value}
                            type="button"
                            onClick={() => handleToggle(option.value)}
                            className={`p-4 rounded-lg border-2 transition-all text-left ${isSelected
                                    ? 'border-primary-500 bg-primary-50'
                                    : 'border-gray-200 hover:border-gray-300'
                                }`}
                        >
                            <div className="flex items-center gap-2">
                                <div
                                    className={`w-4 h-4 rounded border-2 flex items-center justify-center ${isSelected
                                            ? 'border-primary-500 bg-primary-500'
                                            : 'border-gray-300'
                                        }`}
                                >
                                    {isSelected && (
                                        <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                                            <path
                                                fillRule="evenodd"
                                                d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                                                clipRule="evenodd"
                                            />
                                        </svg>
                                    )}
                                </div>
                                <span className={`font-medium ${isSelected ? 'text-primary-700' : 'text-gray-900'}`}>
                                    {option.label}
                                </span>
                            </div>
                            <p className="mt-1 text-xs text-gray-500">{option.description}</p>
                        </button>
                    );
                })}
            </div>
        </div>
    );
};
