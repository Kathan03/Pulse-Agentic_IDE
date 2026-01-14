/**
 * Settings Tab - VS Code-style Settings Interface
 *
 * Displays as a tab in the editor area with sections for:
 * - API Keys (OpenAI, Anthropic) - stored in platformdirs
 * - AI Models selection
 * - Appearance (theme)
 * - Editor preferences
 */

import { useState, useEffect, useCallback } from 'react';
import { useTheme, themes, ThemeIcon, type ThemeName } from '@/contexts/ThemeContext';
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
  const [activeSection, setActiveSection] = useState<'apikeys' | 'appearance' | 'editor' | 'agent'>('apikeys');

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
  const [keyStatus, setKeyStatus] = useState<APIKeyStatus | null>(null);
  const [configPath, setConfigPath] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<'openai' | 'anthropic' | null>(null);
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

  const handleSaveKey = useCallback(async (provider: 'openai' | 'anthropic') => {
    const key = provider === 'openai' ? openaiKey : anthropicKey;

    if (!key.trim()) {
      setMessage({ type: 'error', text: 'Please enter an API key' });
      return;
    }

    setSaving(provider);
    setMessage(null);

    try {
      await updateAPIKey(provider, key.trim());
      setMessage({ type: 'success', text: `${provider === 'openai' ? 'OpenAI' : 'Anthropic'} API key saved successfully!` });

      // Clear the input and refresh status
      if (provider === 'openai') {
        setOpenaiKey('');
      } else {
        setAnthropicKey('');
      }

      const status = await fetchAPIKeyStatus();
      setKeyStatus(status);
    } catch (error) {
      setMessage({ type: 'error', text: `Failed to save key: ${error instanceof Error ? error.message : 'Unknown error'}` });
    } finally {
      setSaving(null);
    }
  }, [openaiKey, anthropicKey]);

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
          <select className="w-32 px-3 py-1.5 bg-pulse-input border border-pulse-border rounded text-sm focus:outline-none focus:border-pulse-primary">
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
          <select className="w-32 px-3 py-1.5 bg-pulse-input border border-pulse-border rounded text-sm focus:outline-none focus:border-pulse-primary">
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

  // Available models
  const availableModels = [
    'gpt-4o',
    'gpt-4o-mini',
    'gpt-4-turbo',
    'claude-3-5-sonnet-20241022',
    'claude-3-5-haiku-20241022',
    'claude-3-opus-20240229',
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
            value={settings?.models.master_agent || 'gpt-4o'}
            onChange={(e) => handleModelChange('master_agent', e.target.value)}
            disabled={saving}
            className="w-48 px-3 py-1.5 bg-pulse-input border border-pulse-border rounded text-sm focus:outline-none focus:border-pulse-primary disabled:opacity-50"
          >
            {availableModels.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </SettingRow>

        <SettingRow
          label="CrewAI Coder Model"
          description="Model for the CrewAI code generation agent"
        >
          <select
            value={settings?.models.crew_coder || 'gpt-4o-mini'}
            onChange={(e) => handleModelChange('crew_coder', e.target.value)}
            disabled={saving}
            className="w-48 px-3 py-1.5 bg-pulse-input border border-pulse-border rounded text-sm focus:outline-none focus:border-pulse-primary disabled:opacity-50"
          >
            {availableModels.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </SettingRow>

        <SettingRow
          label="AutoGen Auditor Model"
          description="Model for the AutoGen code auditing agent"
        >
          <select
            value={settings?.models.autogen_auditor || 'gpt-4o-mini'}
            onChange={(e) => handleModelChange('autogen_auditor', e.target.value)}
            disabled={saving}
            className="w-48 px-3 py-1.5 bg-pulse-input border border-pulse-border rounded text-sm focus:outline-none focus:border-pulse-primary disabled:opacity-50"
          >
            {availableModels.map((m) => (
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
