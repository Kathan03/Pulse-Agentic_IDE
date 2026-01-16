/**
 * ChatHistory - Sidebar for conversation history
 *
 * Shows past agent chats and allows creating new conversations.
 * Uses the conversations REST API.
 */

import { useState, useEffect, useCallback } from 'react';
import { useAgentStore } from '@/stores/agentStore';
import { useWorkspaceStore } from '@/stores/workspaceStore';

interface Conversation {
    id: string;
    title: string | null;
    created_at: string;
    updated_at: string;
    message_count?: number;
    first_message?: string | null;
}

const API_BASE_URL = 'http://127.0.0.1:8765';

export function ChatHistory() {
    const [conversations, setConversations] = useState<Conversation[]>([]);
    const [isOpen, setIsOpen] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const conversationId = useAgentStore((s) => s.conversationId);
    const clearMessages = useAgentStore((s) => s.clearMessages);
    const projectRoot = useWorkspaceStore((s) => s.projectRoot);

    // Fetch conversations list
    const fetchConversations = useCallback(async () => {
        setIsLoading(true);
        try {
            if (!projectRoot) {
                console.warn('No project root set, cannot fetch conversations');
                setConversations([]);
                setIsLoading(false);
                return;
            }

            const encodedPath = encodeURIComponent(projectRoot);
            const response = await fetch(`${API_BASE_URL}/api/conversations?limit=20&project_root=${encodedPath}`);
            if (response.ok) {
                const data = await response.json();
                setConversations(data);
            } else {
                console.error('Failed to fetch conversations:', response.status);
                setConversations([]);
            }
        } catch (error) {
            console.error('Failed to fetch conversations:', error);
            setConversations([]);
        } finally {
            setIsLoading(false);
        }
    }, [projectRoot]);

    // Load conversations when dropdown opens
    useEffect(() => {
        if (isOpen) {
            fetchConversations();
        }
    }, [isOpen, fetchConversations]);

    // Create new conversation
    const handleNewChat = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/conversations`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: null }),
            });

            if (response.ok) {
                const data = await response.json();
                clearMessages();
                // The websocket will handle setting the new conversation ID
                setIsOpen(false);
            }
        } catch (error) {
            console.error('Failed to create conversation:', error);
        }
    };

    // Load existing conversation
    const handleSelectConversation = async (conv: Conversation) => {
        try {
            if (!projectRoot) {
                console.error('No project root set');
                return;
            }
            const encodedPath = encodeURIComponent(projectRoot);
            const response = await fetch(`${API_BASE_URL}/api/conversations/${conv.id}?project_root=${encodedPath}`);
            if (response.ok) {
                const data = await response.json();
                clearMessages();

                // Add existing messages to store
                if (data.messages && data.messages.length > 0) {
                    data.messages.forEach((msg: { role: string; content: string }) => {
                        useAgentStore.getState().addMessage({
                            role: msg.role as 'user' | 'assistant',
                            content: msg.content,
                        });
                    });
                }

                setIsOpen(false);
            }
        } catch (error) {
            console.error('Failed to load conversation:', error);
        }
    };

    // Delete conversation
    const handleDeleteConversation = async (e: React.MouseEvent, convId: string) => {
        e.stopPropagation();

        if (!confirm('Delete this conversation?')) return;
        if (!projectRoot) {
            console.error('No project root set');
            return;
        }

        try {
            const encodedPath = encodeURIComponent(projectRoot);
            const response = await fetch(`${API_BASE_URL}/api/conversations/${convId}?project_root=${encodedPath}`, {
                method: 'DELETE',
            });

            if (response.ok) {
                setConversations((prev) => prev.filter((c) => c.id !== convId));
            }
        } catch (error) {
            console.error('Failed to delete conversation:', error);
        }
    };

    // Format relative time
    const formatTime = (dateString: string) => {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return date.toLocaleDateString();
    };

    return (
        <div className="relative">
            {/* Trigger Button */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="p-1.5 rounded hover:bg-pulse-bg-tertiary transition-colors"
                title="Chat History"
            >
                <HistoryIcon />
            </button>

            {/* Dropdown */}
            {isOpen && (
                <>
                    {/* Backdrop */}
                    <div
                        className="fixed inset-0 z-40"
                        onClick={() => setIsOpen(false)}
                    />

                    {/* Panel */}
                    <div className="absolute right-0 top-full mt-1 z-50 w-72 bg-pulse-bg-secondary border border-pulse-border rounded-lg shadow-lg overflow-hidden">
                        {/* Header */}
                        <div className="flex items-center justify-between px-3 py-2 border-b border-pulse-border">
                            <span className="text-xs font-semibold text-pulse-fg-muted uppercase tracking-wide">
                                Chat History
                            </span>
                            <button
                                onClick={handleNewChat}
                                className="flex items-center gap-1 px-2 py-1 text-xs bg-pulse-primary text-white rounded hover:bg-pulse-primary/90 transition-colors"
                            >
                                <PlusIcon />
                                New Chat
                            </button>
                        </div>

                        {/* Conversations List */}
                        <div className="max-h-80 overflow-auto">
                            {isLoading ? (
                                <div className="p-4 text-center text-pulse-fg-muted text-xs">
                                    Loading...
                                </div>
                            ) : conversations.length === 0 ? (
                                <div className="p-4 text-center text-pulse-fg-muted text-xs">
                                    No past conversations
                                </div>
                            ) : (
                                <div className="p-1">
                                    {conversations.map((conv) => (
                                        <button
                                            key={conv.id}
                                            onClick={() => handleSelectConversation(conv)}
                                            className={`w-full px-3 py-2 text-left rounded hover:bg-pulse-bg-tertiary transition-colors group ${conv.id === conversationId ? 'bg-pulse-primary/10' : ''
                                                }`}
                                        >
                                            <div className="flex items-start justify-between gap-2">
                                                <div className="flex-1 min-w-0">
                                                    <div className="text-sm text-pulse-fg truncate">
                                                        {conv.first_message || conv.title || 'New Chat'}
                                                    </div>
                                                    <div className="flex items-center gap-2 text-xs text-pulse-fg-muted mt-0.5">
                                                        <span>{formatTime(conv.updated_at)}</span>
                                                        {conv.message_count !== undefined && (
                                                            <span>• {conv.message_count} msgs</span>
                                                        )}
                                                    </div>
                                                </div>
                                                <button
                                                    onClick={(e) => handleDeleteConversation(e, conv.id)}
                                                    className="p-1 opacity-0 group-hover:opacity-100 hover:bg-red-500/20 rounded transition-all"
                                                    title="Delete"
                                                >
                                                    <TrashIcon />
                                                </button>
                                            </div>
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}

function HistoryIcon() {
    return (
        <svg viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4 text-pulse-fg-muted">
            <path d="M8 16A8 8 0 108 0a8 8 0 000 16zm0-14.5a6.5 6.5 0 110 13 6.5 6.5 0 010-13zM7.25 4v4.5l3.5 2.1.75-1.23-2.75-1.65V4h-1.5z" />
        </svg>
    );
}

function PlusIcon() {
    return (
        <svg viewBox="0 0 16 16" fill="currentColor" className="w-3 h-3">
            <path d="M8 0a.75.75 0 01.75.75v6.5h6.5a.75.75 0 010 1.5h-6.5v6.5a.75.75 0 01-1.5 0v-6.5H.75a.75.75 0 010-1.5h6.5V.75A.75.75 0 018 0z" />
        </svg>
    );
}

function TrashIcon() {
    return (
        <svg viewBox="0 0 16 16" fill="currentColor" className="w-3.5 h-3.5 text-red-400">
            <path d="M11 1.75V3h2.25a.75.75 0 010 1.5H2.75a.75.75 0 010-1.5H5V1.75C5 .784 5.784 0 6.75 0h2.5C10.216 0 11 .784 11 1.75zm-5 0V3h4V1.75a.25.25 0 00-.25-.25h-3.5a.25.25 0 00-.25.25zM4.496 6.675a.75.75 0 10-1.492.15l.66 6.6A1.75 1.75 0 005.405 15h5.19c.9 0 1.652-.681 1.741-1.575l.66-6.6a.75.75 0 00-1.492-.15l-.66 6.6a.25.25 0 01-.249.225h-5.19a.25.25 0 01-.249-.225l-.66-6.6z" />
        </svg>
    );
}
