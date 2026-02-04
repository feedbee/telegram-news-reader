
import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Loader2, Send, Save, RefreshCw, Hash, Calendar, Layers, ExternalLink } from 'lucide-react';
import './App.css';

const Login = () => {
    const { login } = useAuth();
    const [error, setError] = useState('');

    const handleLogin = async () => {
        try {
            setError('');
            await login();
        } catch (err) {
            setError('Failed to sign in. Please try again.');
            console.error(err);
        }
    };

    return (
        <div className="login-container">
            <div className="card glass-card login-card">
                <h1>News Reader Console</h1>
                <p>Please sign in to access the console.</p>
                {error && <p className="error-text">{error}</p>}
                <button className="primary-button" onClick={handleLogin}>
                    Sign in with Google
                </button>
            </div>
        </div>
    );
};

const Console = () => {
    const { logout, currentUser, getToken } = useAuth();
    const [channels, setChannels] = useState([]);
    const [selectedChannel, setSelectedChannel] = useState('');
    const [lastMessageId, setLastMessageId] = useState(() => {
        return localStorage.getItem('last_message_id') || '';
    });
    const [loading, setLoading] = useState(false);
    const [summary, setSummary] = useState('');
    const [metadata, setMetadata] = useState(null);
    const [userMetadata, setUserMetadata] = useState(null);
    const [error, setError] = useState('');

    // 1. Fetch Channels
    // 1. Sync User & Fetch Channels
    useEffect(() => {
        const init = async () => {
            if (!currentUser) return;
            try {
                const token = await getToken();

                // A. Sync User
                const syncRes = await fetch('/api/users/sync', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (syncRes.ok) {
                    const syncData = await syncRes.json();
                    setUserMetadata(syncData.metadata);
                }

                // B. Fetch Channels
                const res = await fetch('/api/channels', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (!res.ok) throw new Error('Failed to fetch channels');
                const data = await res.json();
                setChannels(data);
                if (data.length > 0) setSelectedChannel(data[0].channel_id);
            } catch (err) {
                console.error(err);
                setError('Could not connect to the backend service.');
            }
        };
        init();
    }, [currentUser]);

    // 2. Persist Last Message ID
    useEffect(() => {
        if (lastMessageId) {
            localStorage.setItem('last_message_id', lastMessageId);
        }
    }, [lastMessageId]);

    // 3. Handle Summarize
    const handleSummarize = async () => {
        if (!selectedChannel) return;

        setLoading(true);
        setError('');
        setSummary('');
        setMetadata(null);

        try {
            const params = new URLSearchParams({
                channel_id: selectedChannel,
                format: 'MD'
            });
            if (lastMessageId) params.append('last_message_id', lastMessageId);

            const token = await getToken();
            const res = await fetch(`/api/summarize?${params.toString()}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            if (!res.ok) throw new Error('Failed to generate summary');

            // Get Metadata from Headers
            const meta = {
                total: res.headers.get('X-META-MESSAGES-TOTAL'),
                processed: res.headers.get('X-META-MESSAGES-PROCESSED'),
                lastId: res.headers.get('X-META-LAST-MESSAGE-ID'),
                lastTimestamp: res.headers.get('X-META-LAST-MESSAGE-TIMESTAMP'),
            };
            setMetadata(meta);

            // Final fallback for last message ID if processed > 0
            if (meta.lastId && meta.lastId !== 'N/A') {
                setLastMessageId(meta.lastId);
            }

            const text = await res.text();
            setSummary(text);
        } catch (err) {
            setError('Generation failed. Check the transform service status.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="app-container">
            <header className="glass-header">
                <div className="header-content">
                    <h1>News Reader <span className="highlight">Console</span></h1>
                    <div className="user-info">
                        <span className="user-email">{currentUser?.email}</span>
                        <button className="secondary-button small" onClick={logout}>Logout</button>
                    </div>
                </div>
            </header>

            <main className="main-content">
                <section className="config-section">
                    <div className="card glass-card">
                        <h2>Configuration</h2>

                        <div className="form-group">
                            <label>Select Channel</label>
                            <select
                                value={selectedChannel}
                                onChange={(e) => {
                                    const newChannel = e.target.value;
                                    setSelectedChannel(newChannel);
                                    // Pre-fill last message ID from user metadata if available
                                    if (userMetadata?.last_message_ids && userMetadata.last_message_ids[newChannel]) {
                                        setLastMessageId(String(userMetadata.last_message_ids[newChannel]));
                                    } else {
                                        setLastMessageId('');
                                    }
                                }}
                                disabled={loading}
                            >
                                {channels.map(ch => (
                                    <option key={ch.channel_id} value={ch.channel_id}>
                                        {ch.name} ({ch.channel_id})
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div className="form-group">
                            <label>Start from Message ID</label>
                            <div className="input-with-icon">
                                <Hash size={18} className="icon" />
                                <input
                                    type="number"
                                    value={lastMessageId}
                                    onChange={(e) => setLastMessageId(e.target.value)}
                                    placeholder="e.g. 15000"
                                    disabled={loading}
                                />
                            </div>
                            <p className="hint">Defaults to standard lookback if empty.</p>
                        </div>

                        <button
                            className={`primary-button ${loading ? 'loading' : ''}`}
                            onClick={handleSummarize}
                            disabled={loading}
                        >
                            {loading ? <Loader2 className="animate-spin" /> : <Send size={18} />}
                            {loading ? 'Processing...' : 'Generate Summary'}
                        </button>
                    </div>

                    {metadata && (
                        <div className="card glass-card meta-card animate-in">
                            <h3>Generation Details</h3>
                            <div className="meta-grid">
                                <div className="meta-item">
                                    <Layers size={16} />
                                    <span>Total: <strong>{metadata.total}</strong></span>
                                </div>
                                <div className="meta-item">
                                    <RefreshCw size={16} />
                                    <span>Processed: <strong>{metadata.processed}</strong></span>
                                </div>
                                <div className="meta-item">
                                    <Hash size={16} />
                                    <span>Last ID: <strong>{metadata.lastId}</strong></span>
                                </div>
                                <div className="meta-item full">
                                    <Calendar size={16} />
                                    <span>Up to: {metadata.lastTimestamp}</span>
                                </div>
                            </div>
                        </div>
                    )}
                </section>

                <section className="content-section">
                    {error && (
                        <div className="error-box animate-in">
                            <p>{error}</p>
                        </div>
                    )}

                    <div className={`card glass-card summary-card ${summary ? 'has-content' : ''}`}>
                        {!summary && !loading && !error && (
                            <div className="empty-state">
                                <div className="empty-icon">⌘</div>
                                <p>Select a channel and click generate to see the AI summary.</p>
                            </div>
                        )}

                        {loading && (
                            <div className="loading-state">
                                <Loader2 className="animate-spin large" />
                                <p>AI is analyzing messages...</p>
                            </div>
                        )}

                        {summary && (
                            <div className="markdown-content animate-in">
                                <ReactMarkdown
                                    components={{
                                        a: ({ node, ...props }) => (
                                            <a {...props} target="_blank" rel="noopener noreferrer">
                                                {props.children} <ExternalLink size={12} className="link-icon" />
                                            </a>
                                        ),
                                    }}
                                >
                                    {summary}
                                </ReactMarkdown>
                            </div>
                        )}
                    </div>
                </section>
            </main>

            <footer className="glass-footer">
                <p>© 2026 Telegram News Reader Platform</p>
            </footer>
        </div>
    );
};

import { AuthProvider, useAuth } from './AuthContext';

const AppContent = () => {
    const { currentUser } = useAuth();
    return currentUser ? <Console /> : <Login />;
};

const App = () => {
    return (
        <AuthProvider>
            <AppContent />
        </AuthProvider>
    );
};

export default App;
