/**
 * LoadingSpinner - Professional loading indicator component
 */
import React from 'react';

interface LoadingSpinnerProps {
    /** Optional loading message */
    message?: string;
    /** Show as fullscreen overlay */
    fullscreen?: boolean;
    /** Size of the spinner */
    size?: 'sm' | 'md' | 'lg';
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
    message = 'Loading...',
    fullscreen = false,
    size = 'md',
}) => {
    const sizeClasses = {
        sm: 'w-8 h-8',
        md: 'w-12 h-12',
        lg: 'w-16 h-16',
    };

    const spinner = (
        <div className="flex flex-col items-center justify-center gap-4">
            {/* Animated spinner with gradient */}
            <div className={`relative ${sizeClasses[size]}`}>
                <div className="absolute inset-0 rounded-full border-4 border-gray-200"></div>
                <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-primary-600 animate-spin"></div>
                {/* Inner glow effect */}
                <div className="absolute inset-2 rounded-full bg-gradient-to-br from-primary-100 to-primary-50 animate-pulse"></div>
            </div>

            {/* Loading message */}
            {message && (
                <p className="text-gray-700 font-medium text-sm animate-pulse">{message}</p>
            )}
        </div>
    );

    if (fullscreen) {
        return (
            <div className="loading-overlay">
                <div className="loading-content">
                    {spinner}
                </div>
            </div>
        );
    }

    return spinner;
};

export default LoadingSpinner;
