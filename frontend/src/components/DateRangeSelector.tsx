/**
 * Date Range Selector Component
 * Provides preset date ranges and custom date selection
 */
import React, { useState, useEffect } from 'react';

interface DateRangeSelectorProps {
    onDateChange: (startDate: string, endDate: string) => void;
    defaultMonths?: number;
}

type PresetOption = {
    label: string;
    months: number;
};

const presets: PresetOption[] = [
    { label: '3 Months', months: 3 },
    { label: '4 Months', months: 4 },
    { label: '6 Months', months: 6 },
    { label: '1 Year', months: 12 },
];

const formatDate = (date: Date): string => {
    return date.toISOString().split('T')[0];
};

const getDateFromMonthsAgo = (months: number): string => {
    const date = new Date();
    date.setMonth(date.getMonth() - months);
    return formatDate(date);
};

export const DateRangeSelector: React.FC<DateRangeSelectorProps> = ({
    onDateChange,
    defaultMonths = 3,
}) => {
    const [selectedPreset, setSelectedPreset] = useState<number | null>(defaultMonths);
    const [customStartDate, setCustomStartDate] = useState<string>('');
    const [customEndDate, setCustomEndDate] = useState<string>(formatDate(new Date()));
    const [isCustom, setIsCustom] = useState(false);

    useEffect(() => {
        // Set initial date range on mount
        if (selectedPreset) {
            const startDate = getDateFromMonthsAgo(selectedPreset);
            const endDate = formatDate(new Date());
            onDateChange(startDate, endDate);
        }
    }, []);

    const handlePresetClick = (months: number) => {
        setSelectedPreset(months);
        setIsCustom(false);
        const startDate = getDateFromMonthsAgo(months);
        const endDate = formatDate(new Date());
        onDateChange(startDate, endDate);
    };

    const handleCustomClick = () => {
        setSelectedPreset(null);
        setIsCustom(true);
        if (customStartDate && customEndDate) {
            onDateChange(customStartDate, customEndDate);
        }
    };

    const handleCustomDateChange = (start: string, end: string) => {
        setCustomStartDate(start);
        setCustomEndDate(end);
        if (start && end) {
            onDateChange(start, end);
        }
    };

    return (
        <div className="space-y-4">
            <label className="block text-sm font-medium text-gray-700">Date Range</label>

            {/* Preset Buttons */}
            <div className="flex flex-wrap gap-2">
                {presets.map((preset) => (
                    <button
                        key={preset.months}
                        type="button"
                        onClick={() => handlePresetClick(preset.months)}
                        className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${selectedPreset === preset.months && !isCustom
                                ? 'bg-primary-600 text-white'
                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            }`}
                    >
                        {preset.label}
                    </button>
                ))}
                <button
                    type="button"
                    onClick={handleCustomClick}
                    className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${isCustom
                            ? 'bg-primary-600 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                >
                    Custom
                </button>
            </div>

            {/* Custom Date Inputs */}
            {isCustom && (
                <div className="flex gap-4 items-center">
                    <div className="flex-1">
                        <label className="block text-xs text-gray-500 mb-1">Start Date</label>
                        <input
                            type="date"
                            value={customStartDate}
                            onChange={(e) => handleCustomDateChange(e.target.value, customEndDate)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        />
                    </div>
                    <span className="text-gray-500 mt-5">to</span>
                    <div className="flex-1">
                        <label className="block text-xs text-gray-500 mb-1">End Date</label>
                        <input
                            type="date"
                            value={customEndDate}
                            onChange={(e) => handleCustomDateChange(customStartDate, e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        />
                    </div>
                </div>
            )}
        </div>
    );
};
