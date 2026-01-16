/**
 * Settings Tab - VS Code-style Settings Interface
 *
 * Displays as a tab in the editor area with sections for:
 * - API Keys (OpenAI, Anthropic, Google) - stored in platformdirs
 * - AI Models selection
 * - Token Usage statistics
 * - Appearance (theme)
 * - Editor preferences
 */

import { useState, useEffect, useCallback } from 'react';
import { useTheme, themes, ThemeIcon } from '@/contexts/ThemeContext';
import {
  fetchSettings,
  fetchAPIKeyStatus,
  updateAPIKey,
  updateModel,
  updatePreference,
  getConfigPath,
  type Settings,
  type APIKeyStatus,
} from '@/services/settingsApi';

export function SettingsTab() {
  const [activeSection, setActiveSection] = useState<'apikeys' | 'appearance' | 'editor' | 'agent' | 'usage'>('apikeys');

  return (
    <div className="h-full flex flex-col bg-pulse-bg overflow-hidden">
      {/* Header - Search removed per Issue 2 */}
      <div className="p-4 border-b border-pulse-border">
        <h1 className="text-xl font-semibold text-pulse-fg">Settings</h1>
      </div>

      {/* Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Navigation - Icons removed per Issue 11 */}
        <nav className="w-48 border-r border-pulse-border p-2">
          <SectionButton
            active={activeSection === 'apikeys'}
            onClick={() => setActiveSection('apikeys')}
          >
            API Keys
          </SectionButton>
          <SectionButton
            active={activeSection === 'usage'}
            onClick={() => setActiveSection('usage')}
          >
            Usage
          </SectionButton>
          <SectionButton
            active={activeSection === 'appearance'}
            onClick={() => setActiveSection('appearance')}
          >
            Appearance
          </SectionButton>
          <SectionButton
            active={activeSection === 'editor'}
            onClick={() => setActiveSection('editor')}
          >
            Editor
          </SectionButton>
          <SectionButton
            active={activeSection === 'agent'}
            onClick={() => setActiveSection('agent')}
          >
            AI Agent
          </SectionButton>
        </nav>

        {/* Settings Content */}
        <div className="flex-1 overflow-auto p-6">
          {activeSection === 'apikeys' && <APIKeysSettings />}
          {activeSection === 'usage' && <UsageSettings />}
          {activeSection === 'appearance' && <AppearanceSettings />}
          {activeSection === 'editor' && <EditorSettings />}
          {activeSection === 'agent' && <AgentSettings />}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Section Button
// ============================================================================

function SectionButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`
        w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm
        transition-colors
        ${active
          ? 'bg-pulse-selection text-pulse-primary'
          : 'text-pulse-fg-muted hover:bg-pulse-bg-tertiary hover:text-pulse-fg'
        }
      `}
    >
      {children}
    </button>
  );
}

// ============================================================================
// API Keys Settings - Connected to Backend
// ============================================================================

function APIKeysSettings() {
  const [openaiKey, setOpenaiKey] = useState('');
  const [anthropicKey, setAnthropicKey] = useState('');
  const [googleKey, setGoogleKey] = useState('');
  const [keyStatus, setKeyStatus] = useState<APIKeyStatus | null>(null);
  const [configPath, setConfigPath] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<'openai' | 'anthropic' | 'google' | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Load initial status
  useEffect(() => {
    async function loadStatus() {
      try {
        const [status, path] = await Promise.all([
          fetchAPIKeyStatus(),
          getConfigPath(),
        ]);
        setKeyStatus(status);
        setConfigPath(path);
      } catch (error) {
        console.error('Failed to load API key status:', error);
        setMessage({ type: 'error', text: 'Failed to connect to backend. Is the server running?' });
      } finally {
        setLoading(false);
      }
    }
    loadStatus();
  }, []);

  const handleSaveKey = useCallback(async (provider: 'openai' | 'anthropic' | 'google') => {
    const key = provider === 'openai' ? openaiKey : provider === 'anthropic' ? anthropicKey : googleKey;

    if (!key.trim()) {
      setMessage({ type: 'error', text: 'Please enter an API key' });
      return;
    }

    setSaving(provider);
    setMessage(null);

    try {
      await updateAPIKey(provider, key.trim());
      const providerName = provider === 'openai' ? 'OpenAI' : provider === 'anthropic' ? 'Anthropic' : 'Google';
      setMessage({ type: 'success', text: `${providerName} API key saved successfully!` });

      // Clear the input and refresh status
      if (provider === 'openai') {
        setOpenaiKey('');
      } else if (provider === 'anthropic') {
        setAnthropicKey('');
      } else {
        setGoogleKey('');
      }

      const status = await fetchAPIKeyStatus();
      setKeyStatus(status);
    } catch (error) {
      setMessage({ type: 'error', text: `Failed to save key: ${error instanceof Error ? error.message : 'Unknown error'}` });
    } finally {
      setSaving(null);
    }
  }, [openaiKey, anthropicKey, googleKey]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="text-pulse-fg-muted">Loading settings...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <SettingsSection title="API Keys">
        <p className="text-sm text-pulse-fg-muted mb-4">
          Configure your API keys for AI providers. Keys are stored securely on your system.
        </p>

        {message && (
          <div className={`p-3 rounded-lg mb-4 ${message.type === 'success' ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'}`}>
            {message.text}
          </div>
        )}

        {/* OpenAI */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-2">
            <h3 className="text-sm font-medium text-pulse-fg">OpenAI API Key</h3>
            {keyStatus?.openai_configured && (
              <span className="px-2 py-0.5 text-xs bg-green-900/30 text-green-400 rounded">Configured</span>
            )}
          </div>
          <p className="text-xs text-pulse-fg-muted mb-2">
            Get your API key from <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-pulse-primary hover:underline">platform.openai.com</a>
          </p>
          <div className="flex gap-2">
            <input
              type="password"
              placeholder={keyStatus?.openai_configured ? "Enter new key to replace..." : "sk-..."}
              value={openaiKey}
              onChange={(e) => setOpenaiKey(e.target.value)}
              className="flex-1 px-3 py-2 bg-pulse-input border border-pulse-border rounded text-sm focus:outline-none focus:border-pulse-primary"
            />
            <button
              onClick={() => handleSaveKey('openai')}
              disabled={saving === 'openai'}
              className="px-4 py-2 bg-pulse-primary text-white rounded text-sm hover:bg-pulse-primary/90 disabled:opacity-50"
            >
              {saving === 'openai' ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>

        {/* Anthropic */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-2">
            <h3 className="text-sm font-medium text-pulse-fg">Anthropic API Key</h3>
            {keyStatus?.anthropic_configured && (
              <span className="px-2 py-0.5 text-xs bg-green-900/30 text-green-400 rounded">Configured</span>
            )}
          </div>
          <p className="text-xs text-pulse-fg-muted mb-2">
            Get your API key from <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener noreferrer" className="text-pulse-primary hover:underline">console.anthropic.com</a>
          </p>
          <div className="flex gap-2">
            <input
              type="password"
              placeholder={keyStatus?.anthropic_configured ? "Enter new key to replace..." : "sk-ant-..."}
              value={anthropicKey}
              onChange={(e) => setAnthropicKey(e.target.value)}
              className="flex-1 px-3 py-2 bg-pulse-input border border-pulse-border rounded text-sm focus:outline-none focus:border-pulse-primary"
            />
            <button
              onClick={() => handleSaveKey('anthropic')}
              disabled={saving === 'anthropic'}
              className="px-4 py-2 bg-pulse-primary text-white rounded text-sm hover:bg-pulse-primary/90 disabled:opacity-50"
            >
              {saving === 'anthropic' ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>

        {/* Google API Key */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-2">
            <h3 className="text-sm font-medium text-pulse-fg">Google API Key</h3>
            {keyStatus?.google_configured && (
              <span className="px-2 py-0.5 text-xs bg-green-900/30 text-green-400 rounded">Configured</span>
            )}
          </div>
          <p className="text-xs text-pulse-fg-muted mb-2">
            Get your API key from <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener noreferrer" className="text-pulse-primary hover:underline">aistudio.google.com</a>
          </p>
          <div className="flex gap-2">
            <input
              type="password"
              placeholder={keyStatus?.google_configured ? "Enter new key to replace..." : "AIzaSy..."}
              value={googleKey}
              onChange={(e) => setGoogleKey(e.target.value)}
              className="flex-1 px-3 py-2 bg-pulse-input border border-pulse-border rounded text-sm focus:outline-none focus:border-pulse-primary"
            />
            <button
              onClick={() => handleSaveKey('google')}
              disabled={saving === 'google'}
              className="px-4 py-2 bg-pulse-primary text-white rounded text-sm hover:bg-pulse-primary/90 disabled:opacity-50"
            >
              {saving === 'google' ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>

        {/* Config Location */}
        <div className="pt-4 border-t border-pulse-border">
          <p className="text-xs text-pulse-fg-muted">
            Settings stored at: <code className="bg-pulse-bg-secondary px-1 rounded">{configPath || 'Loading...'}</code>
          </p>
        </div>
      </SettingsSection>
    </div>
  );
}

// ============================================================================
// Usage Settings - API Usage Statistics
// ============================================================================

function UsageSettings() {
  const [usageStats, setUsageStats] = useState<{
    total_calls: number;
    total_tokens: number;
    total_prompt_tokens: number;
    total_completion_tokens: number;
    total_cost_usd: number;
    by_model: Array<{
      model: string;
      tokens: number;
      prompt_tokens: number;
      completion_tokens: number;
      cost_usd: number;
      call_count: number;
    }>;
  } | null>(null);

  const [toolStats, setToolStats] = useState<{
    total_calls: number;
    total_successes: number;
    total_failures: number;
    overall_success_rate: number;
    by_tool: Record<string, {
      calls: number;
      successes: number;
      failures: number;
      success_rate: number;
      avg_duration_ms: number;
    }>;
    slow_tools: string[];
    failing_tools: string[];
  } | null>(null);

  const [loading, setLoading] = useState(true);
  const [resettingUsage, setResettingUsage] = useState(false);
  const [resettingTools, setResettingTools] = useState(false);

  const fetchStats = useCallback(async () => {
    try {
      const { fetchUsageStatistics, fetchToolAnalytics } = await import('@/services/settingsApi');
      const [usage, tools] = await Promise.all([
        fetchUsageStatistics(),
        fetchToolAnalytics()
      ]);
      setUsageStats(usage);
      setToolStats(tools);
    } catch (error) {
      console.error('Failed to fetch usage stats:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch and polling every 5 seconds
  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  const handleResetUsage = async () => {
    setResettingUsage(true);
    try {
      const { resetUsageStatistics } = await import('@/services/settingsApi');
      await resetUsageStatistics();
      await fetchStats();
    } catch (error) {
      console.error('Failed to reset usage stats:', error);
    } finally {
      setResettingUsage(false);
    }
  };

  const handleResetTools = async () => {
    setResettingTools(true);
    try {
      const { resetToolAnalytics } = await import('@/services/settingsApi');
      await resetToolAnalytics();
      await fetchStats();
    } catch (error) {
      console.error('Failed to reset tool analytics:', error);
    } finally {
      setResettingTools(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <SettingsSection title="API Usage Statistics">
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin w-6 h-6 border-2 border-pulse-primary border-t-transparent rounded-full" />
          </div>
        </SettingsSection>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* API Usage Statistics */}
      <SettingsSection title="API Usage Statistics">
        <div className="flex justify-between items-start mb-4">
          <p className="text-sm text-pulse-fg-muted">
            Track your API token usage and estimated costs.
          </p>
          <button
            onClick={handleResetUsage}
            disabled={resettingUsage}
            className="px-3 py-1 text-xs bg-pulse-bg-tertiary hover:bg-pulse-input rounded transition-colors disabled:opacity-50"
          >
            {resettingUsage ? 'Resetting...' : 'Reset'}
          </button>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          <div className="bg-pulse-bg-secondary p-4 rounded-lg text-center">
            <div className="text-2xl font-bold text-pulse-primary">
              {usageStats?.total_calls ?? 0}
            </div>
            <div className="text-xs text-pulse-fg-muted mt-1">Total API Calls</div>
          </div>
          <div className="bg-pulse-bg-secondary p-4 rounded-lg text-center">
            <div className="text-2xl font-bold text-pulse-fg">
              {(usageStats?.total_tokens ?? 0).toLocaleString()}
            </div>
            <div className="text-xs text-pulse-fg-muted mt-1">Total Tokens</div>
          </div>
          <div className="bg-pulse-bg-secondary p-4 rounded-lg text-center">
            <div className="text-2xl font-bold text-pulse-success">
              ${(usageStats?.total_cost_usd ?? 0).toFixed(4)}
            </div>
            <div className="text-xs text-pulse-fg-muted mt-1">Est. Total Cost</div>
          </div>
        </div>

        {/* Model Breakdown */}
        {usageStats && usageStats.by_model.length > 0 && (
          <>
            <h3 className="text-sm font-medium text-pulse-fg mb-3">Usage by Model</h3>
            <div className="space-y-2">
              {usageStats.by_model.map((model) => (
                <ModelUsageRow key={model.model} {...model} />
              ))}
            </div>
          </>
        )}

        <p className="text-xs text-pulse-fg-muted mt-4">
          Usage statistics are session-based and reset when the application restarts.
        </p>
      </SettingsSection>

      {/* Tool Usage Analytics */}
      <SettingsSection title="Tool Usage Analytics">
        <div className="flex justify-between items-start mb-4">
          <p className="text-sm text-pulse-fg-muted">
            Track tool execution success rates and performance.
          </p>
          <button
            onClick={handleResetTools}
            disabled={resettingTools}
            className="px-3 py-1 text-xs bg-pulse-bg-tertiary hover:bg-pulse-input rounded transition-colors disabled:opacity-50"
          >
            {resettingTools ? 'Resetting...' : 'Reset'}
          </button>
        </div>

        {/* Tool Summary */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          <div className="bg-pulse-bg-secondary p-4 rounded-lg text-center">
            <div className="text-2xl font-bold text-pulse-primary">
              {toolStats?.total_calls ?? 0}
            </div>
            <div className="text-xs text-pulse-fg-muted mt-1">Total Tool Calls</div>
          </div>
          <div className="bg-pulse-bg-secondary p-4 rounded-lg text-center">
            <div className="text-2xl font-bold text-pulse-success">
              {toolStats?.total_successes ?? 0}
            </div>
            <div className="text-xs text-pulse-fg-muted mt-1">Successful</div>
          </div>
          <div className="bg-pulse-bg-secondary p-4 rounded-lg text-center">
            <div className={`text-2xl font-bold ${(toolStats?.total_failures ?? 0) > 0 ? 'text-pulse-error' : 'text-pulse-fg'}`}>
              {toolStats?.total_failures ?? 0}
            </div>
            <div className="text-xs text-pulse-fg-muted mt-1">Failed</div>
          </div>
        </div>

        {/* Tool Breakdown */}
        {toolStats && Object.keys(toolStats.by_tool).length > 0 && (
          <>
            <h3 className="text-sm font-medium text-pulse-fg mb-3">Tool Breakdown</h3>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {Object.entries(toolStats.by_tool).map(([toolName, stats]) => (
                <ToolUsageRow key={toolName} name={toolName} {...stats} />
              ))}
            </div>
          </>
        )}

        <p className="text-xs text-pulse-fg-muted mt-4">
          Tool analytics persist across sessions and are stored in the project.
        </p>
      </SettingsSection>
    </div>
  );
}

function ModelUsageRow({
  model,
  tokens,
  call_count,
  cost_usd
}: {
  model: string;
  tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  call_count: number;
  cost_usd: number;
}) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between p-3 bg-pulse-bg-secondary rounded-lg gap-2">
      <span className="text-sm font-medium text-pulse-fg font-mono">{model}</span>
      <div className="flex flex-wrap items-center gap-3 sm:gap-4 text-xs text-pulse-fg-muted">
        <span>{call_count.toLocaleString()} calls</span>
        <span>{tokens.toLocaleString()} tokens</span>
        <span className="text-pulse-success">${cost_usd.toFixed(4)}</span>
      </div>
    </div>
  );
}

function ToolUsageRow({
  name,
  calls,
  successes: _successes,
  failures: _failures,
  success_rate,
  avg_duration_ms
}: {
  name: string;
  calls: number;
  successes: number;
  failures: number;
  success_rate: number;
  avg_duration_ms: number;
}) {
  const rateColor = success_rate >= 0.9 ? 'text-pulse-success' : success_rate >= 0.7 ? 'text-pulse-warning' : 'text-pulse-error';

  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between p-3 bg-pulse-bg-secondary rounded-lg gap-2">
      <span className="text-sm font-medium text-pulse-fg">{name}</span>
      <div className="flex flex-wrap items-center gap-3 sm:gap-4 text-xs text-pulse-fg-muted">
        <span>{calls} calls</span>
        <span className={rateColor}>{(success_rate * 100).toFixed(0)}% success</span>
        <span>{avg_duration_ms.toFixed(0)}ms avg</span>
      </div>
    </div>
  );
}


// ============================================================================
// Appearance Settings
// ============================================================================

function AppearanceSettings() {
  const { theme, setTheme } = useTheme();
  const themeList = Object.values(themes);

  return (
    <div className="space-y-6">
      <SettingsSection title="Color Theme">
        <p className="text-sm text-pulse-fg-muted mb-4">
          Select a color theme for the application.
        </p>
        <div className="grid grid-cols-2 gap-3">
          {themeList.map((t) => (
            <button
              key={t.name}
              onClick={() => setTheme(t.name)}
              className={`
                flex items-center gap-3 p-3 rounded-lg border transition-all
                ${theme.name === t.name
                  ? 'border-pulse-primary bg-pulse-selection'
                  : 'border-pulse-border hover:border-pulse-fg-muted'
                }
              `}
            >
              <div
                className="w-8 h-8 rounded-md flex items-center justify-center"
                style={{ backgroundColor: t.colors.bg }}
              >
                <ThemeIcon icon={t.icon} className="w-5 h-5" style={{ color: t.colors.primary }} />
              </div>
              <div className="text-left">
                <div className="text-sm font-medium text-pulse-fg">{t.label}</div>
                <div className="text-xs text-pulse-fg-muted">
                  {t.isDark ? 'Dark' : 'Light'} theme
                </div>
              </div>
              {theme.name === t.name && (
                <span className="ml-auto text-pulse-success">✓</span>
              )}
            </button>
          ))}
        </div>
      </SettingsSection>

      <SettingsSection title="UI Density">
        <div className="flex gap-3">
          <label className="flex items-center gap-2">
            <input type="radio" name="density" defaultChecked className="accent-[var(--pulse-primary)]" />
            <span className="text-sm text-pulse-fg">Comfortable</span>
          </label>
          <label className="flex items-center gap-2">
            <input type="radio" name="density" className="accent-[var(--pulse-primary)]" />
            <span className="text-sm text-pulse-fg">Compact</span>
          </label>
        </div>
      </SettingsSection>
    </div>
  );
}

// ============================================================================
// Editor Settings
// ============================================================================

function EditorSettings() {
  return (
    <div className="space-y-6">
      <SettingsSection title="Font">
        <SettingRow
          label="Font Family"
          description="Controls the font family for the editor"
        >
          <input
            type="text"
            defaultValue="Cascadia Code, Consolas, monospace"
            className="w-64 px-3 py-1.5 bg-pulse-input border border-pulse-border rounded text-sm focus:outline-none focus:border-pulse-primary"
          />
        </SettingRow>

        <SettingRow
          label="Font Size"
          description="Controls the font size in pixels"
        >
          <input
            type="number"
            defaultValue={14}
            className="w-20 px-3 py-1.5 bg-pulse-input border border-pulse-border rounded text-sm focus:outline-none focus:border-pulse-primary"
          />
        </SettingRow>

        <SettingRow
          label="Line Height"
          description="Controls the line height"
        >
          <input
            type="number"
            defaultValue={1.5}
            step={0.1}
            className="w-20 px-3 py-1.5 bg-pulse-input border border-pulse-border rounded text-sm focus:outline-none focus:border-pulse-primary"
          />
        </SettingRow>
      </SettingsSection>

      <SettingsSection title="Display">
        <SettingRow
          label="Word Wrap"
          description="Controls how lines should wrap"
        >
          <select aria-label="Word Wrap" className="w-32 px-3 py-1.5 bg-pulse-input border border-pulse-border rounded text-sm focus:outline-none focus:border-pulse-primary">
            <option>off</option>
            <option>on</option>
            <option>wordWrapColumn</option>
            <option>bounded</option>
          </select>
        </SettingRow>

        <SettingRow
          label="Minimap"
          description="Controls whether the minimap is shown"
        >
          <input type="checkbox" defaultChecked className="accent-[var(--pulse-primary)]" />
        </SettingRow>

        <SettingRow
          label="Line Numbers"
          description="Controls the display of line numbers"
        >
          <select aria-label="Line Numbers" className="w-32 px-3 py-1.5 bg-pulse-input border border-pulse-border rounded text-sm focus:outline-none focus:border-pulse-primary">
            <option>on</option>
            <option>off</option>
            <option>relative</option>
            <option>interval</option>
          </select>
        </SettingRow>
      </SettingsSection>
    </div>
  );
}

// ============================================================================
// Agent Settings - Connected to Backend
// ============================================================================

function AgentSettings() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Available models - ONLY user-specified models
  const availableModels = {
    openai: [
      'gpt-5.2', 'gpt-5.1', 'gpt-5', 'gpt-5-mini', 'gpt-5-nano',
      'gpt-5.2-codex', 'gpt-5.1-codex-max', 'gpt-5.1-codex',
      'gpt-5.2-pro', 'gpt-5-pro'
    ],
    anthropic: [
      'claude-sonnet-4.5', 'claude-opus-4.5'
    ],
    google: [
      'gemini-3-pro', 'gemini-3-flash'
    ]
  };

  // Flatten for dropdown
  const allModels = [
    ...availableModels.openai,
    ...availableModels.anthropic,
    ...availableModels.google
  ];

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchSettings();
        setSettings(data);
      } catch (error) {
        console.error('Failed to load settings:', error);
        setMessage({ type: 'error', text: 'Failed to connect to backend' });
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const handleModelChange = async (component: 'master_agent' | 'crew_coder' | 'autogen_auditor', model: string) => {
    if (!settings) return;

    setSaving(true);
    setMessage(null);

    try {
      await updateModel(component, model);
      setSettings({
        ...settings,
        models: { ...settings.models, [component]: model },
      });
      setMessage({ type: 'success', text: 'Model updated' });
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to update model' });
    } finally {
      setSaving(false);
    }
  };

  const handlePreferenceChange = async (key: string, value: boolean) => {
    if (!settings) return;

    setSaving(true);
    setMessage(null);

    try {
      await updatePreference(key, value);
      setSettings({
        ...settings,
        preferences: { ...settings.preferences, [key]: value },
      });
      setMessage({ type: 'success', text: 'Preference updated' });
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to update preference' });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="text-pulse-fg-muted">Loading settings...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {message && (
        <div className={`p-3 rounded-lg ${message.type === 'success' ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'}`}>
          {message.text}
        </div>
      )}

      <SettingsSection title="AI Models">
        <SettingRow
          label="Master Agent Model"
          description="The primary model for agent orchestration"
        >
          <select
            value={settings?.models.master_agent || 'gpt-5'}
            onChange={(e) => handleModelChange('master_agent', e.target.value)}
            disabled={saving}
            title="Select Master Agent Model"
            className="w-52 px-3 py-1.5 bg-pulse-input border border-pulse-border rounded text-sm focus:outline-none focus:border-pulse-primary disabled:opacity-50"
          >
            {allModels.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </SettingRow>

        <SettingRow
          label="CrewAI Coder Model"
          description="Model for the CrewAI code generation agent"
        >
          <select
            value={settings?.models.crew_coder || 'gpt-5-mini'}
            onChange={(e) => handleModelChange('crew_coder', e.target.value)}
            disabled={saving}
            title="Select CrewAI Coder Model"
            className="w-52 px-3 py-1.5 bg-pulse-input border border-pulse-border rounded text-sm focus:outline-none focus:border-pulse-primary disabled:opacity-50"
          >
            {allModels.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </SettingRow>

        <SettingRow
          label="AutoGen Auditor Model"
          description="Model for the AutoGen code auditing agent"
        >
          <select
            value={settings?.models.autogen_auditor || 'gpt-5-mini'}
            onChange={(e) => handleModelChange('autogen_auditor', e.target.value)}
            disabled={saving}
            title="Select AutoGen Auditor Model"
            className="w-52 px-3 py-1.5 bg-pulse-input border border-pulse-border rounded text-sm focus:outline-none focus:border-pulse-primary disabled:opacity-50"
          >
            {allModels.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </SettingRow>
      </SettingsSection>

      <SettingsSection title="Agent Features">
        <SettingRow
          label="Enable CrewAI Builder"
          description="Use CrewAI for complex feature implementations"
        >
          <input
            type="checkbox"
            checked={settings?.preferences.enable_crew ?? true}
            onChange={(e) => handlePreferenceChange('enable_crew', e.target.checked)}
            disabled={saving}
            className="accent-[var(--pulse-primary)]"
          />
        </SettingRow>

        <SettingRow
          label="Enable AutoGen Auditor"
          description="Use AutoGen for project health diagnostics"
        >
          <input
            type="checkbox"
            checked={settings?.preferences.enable_autogen ?? true}
            onChange={(e) => handlePreferenceChange('enable_autogen', e.target.checked)}
            disabled={saving}
            className="accent-[var(--pulse-primary)]"
          />
        </SettingRow>
      </SettingsSection>

      <SettingsSection title="Behavior">
        <SettingRow
          label="Max Iterations"
          description="Maximum number of agent iterations per run"
        >
          <input
            type="number"
            defaultValue={10}
            min={1}
            max={50}
            className="w-20 px-3 py-1.5 bg-pulse-input border border-pulse-border rounded text-sm focus:outline-none focus:border-pulse-primary"
          />
        </SettingRow>

        <SettingRow
          label="Auto-approve patches"
          description="Automatically approve safe file patches"
        >
          <input type="checkbox" className="accent-[var(--pulse-primary)]" />
        </SettingRow>

        <SettingRow
          label="Require approval for terminals"
          description="Always require approval for terminal commands"
        >
          <input type="checkbox" defaultChecked className="accent-[var(--pulse-primary)]" />
        </SettingRow>
      </SettingsSection>
    </div>
  );
}

// ============================================================================
// Helper Components
// ============================================================================

function SettingsSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="text-lg font-medium text-pulse-fg mb-4 pb-2 border-b border-pulse-border">
        {title}
      </h2>
      {children}
    </section>
  );
}

function SettingRow({
  label,
  description,
  children,
}: {
  label: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between py-3 border-b border-pulse-border last:border-b-0">
      <div className="mr-4">
        <div className="text-sm font-medium text-pulse-fg">{label}</div>
        <div className="text-xs text-pulse-fg-muted mt-0.5">{description}</div>
      </div>
      <div className="flex-shrink-0">{children}</div>
    </div>
  );
}

// Settings section icons removed per Issue 11
