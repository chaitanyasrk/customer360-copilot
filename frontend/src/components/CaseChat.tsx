/**
 * CaseChat - Chat interface for asking questions about a case
 */
import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { apiService } from '@/services/api';
import { MessageCircle, Send, Bot, User, Info } from 'lucide-react';
import type { CaseQueryResponse } from '@/types';

interface ChatMessage {
    id: string;
    type: 'user' | 'assistant';
    content: string;
    sources?: string[];
    confidence?: number;
    timestamp: Date;
}

interface CaseChatProps {
    caseId: string;
}

export const CaseChat: React.FC<CaseChatProps> = ({ caseId }) => {
    const [question, setQuestion] = useState('');
    const [messages, setMessages] = useState<ChatMessage[]>([]);

    // Query mutation
    const queryMutation = useMutation({
        mutationFn: (q: string) => apiService.queryCaseDetails(caseId, q),
        onSuccess: (data: CaseQueryResponse) => {
            setMessages((prev) => [
                ...prev,
                {
                    id: `assistant-${Date.now()}`,
                    type: 'assistant',
                    content: data.answer,
                    sources: data.sources,
                    confidence: data.confidence,
                    timestamp: new Date(),
                },
            ]);
        },
        onError: (error: Error) => {
            setMessages((prev) => [
                ...prev,
                {
                    id: `error-${Date.now()}`,
                    type: 'assistant',
                    content: `Sorry, I encountered an error: ${error.message}`,
                    timestamp: new Date(),
                },
            ]);
        },
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!question.trim() || queryMutation.isPending) return;

        // Add user message
        setMessages((prev) => [
            ...prev,
            {
                id: `user-${Date.now()}`,
                type: 'user',
                content: question,
                timestamp: new Date(),
            },
        ]);

        // Send query
        queryMutation.mutate(question);
        setQuestion('');
    };

    return (
        <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <MessageCircle className="w-5 h-5 text-primary-600" />
                Ask About This Case
            </h3>

            {/* Chat Messages */}
            <div className="bg-gray-50 rounded-lg p-4 mb-4 min-h-[200px] max-h-[400px] overflow-y-auto">
                {messages.length === 0 ? (
                    <div className="text-center text-gray-500 py-8">
                        <Bot className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                        <p>Ask any question about this case.</p>
                        <p className="text-sm mt-2">
                            Try asking about the customer, account details, or case history.
                        </p>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {messages.map((msg) => (
                            <div
                                key={msg.id}
                                className={`flex gap-3 ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
                            >
                                {msg.type === 'assistant' && (
                                    <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0">
                                        <Bot className="w-4 h-4 text-primary-600" />
                                    </div>
                                )}
                                <div
                                    className={`max-w-[80%] rounded-lg p-3 ${msg.type === 'user'
                                            ? 'bg-primary-600 text-white'
                                            : 'bg-white border border-gray-200'
                                        }`}
                                >
                                    <p className={msg.type === 'user' ? 'text-white' : 'text-gray-700'}>
                                        {msg.content}
                                    </p>
                                    {msg.type === 'assistant' && msg.sources && msg.sources.length > 0 && (
                                        <div className="mt-2 pt-2 border-t border-gray-100">
                                            <div className="flex items-center gap-1 text-xs text-gray-500">
                                                <Info className="w-3 h-3" />
                                                Sources: {msg.sources.join(', ')}
                                            </div>
                                            {msg.confidence !== undefined && (
                                                <div className="text-xs text-gray-400 mt-1">
                                                    Confidence: {(msg.confidence * 100).toFixed(0)}%
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                                {msg.type === 'user' && (
                                    <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0">
                                        <User className="w-4 h-4 text-gray-600" />
                                    </div>
                                )}
                            </div>
                        ))}
                        {queryMutation.isPending && (
                            <div className="flex gap-3">
                                <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0">
                                    <Bot className="w-4 h-4 text-primary-600" />
                                </div>
                                <div className="bg-white border border-gray-200 rounded-lg p-3">
                                    <div className="flex items-center gap-2">
                                        <div className="w-2 h-2 bg-primary-600 rounded-full animate-bounce"></div>
                                        <div className="w-2 h-2 bg-primary-600 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                                        <div className="w-2 h-2 bg-primary-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                                        <span className="text-gray-500 text-sm ml-2">Thinking...</span>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Input Form */}
            <form onSubmit={handleSubmit} className="flex gap-2">
                <input
                    type="text"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="Ask about the case, customer, or related information..."
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    disabled={queryMutation.isPending}
                />
                <button
                    type="submit"
                    disabled={!question.trim() || queryMutation.isPending}
                    className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                >
                    <Send className="w-4 h-4" />
                    Ask
                </button>
            </form>
        </div>
    );
};

export default CaseChat;
