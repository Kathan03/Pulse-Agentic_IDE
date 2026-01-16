/**
 * Settings API Service
 *
 * Communicates with the Python backend to manage user settings
 * including API keys, model preferences, and other configurations.
 */

const DEFAULT_PORT = 8765;

/**
 * Get the backend API base URL.
 */
async function getBaseUrl(): Promise<string> {
  let port = DEFAULT_PORT;

  try {
    if (window.pulseAPI?.backend?.getPort) {
      port = await window.pulseAPI.backend.getPort();
    }
  } catch (error) {
    console.warn('[SettingsAPI] Failed to get backend port, using default:', error);
  }

  return `http://127.0.0.1:${port}/api`;
}

/**
 * Settings structure returned from the API.
 */
export interface Settings {
  api_keys: {
    openai: string;
    anthropic: string;
    google: string;
  };
  models: {
    master_agent: string;
    crew_coder: string;
    autogen_auditor: string;
  };
  preferences: {
    theme: string;
    enable_autogen: boolean;
    enable_crew: boolean;
    [key: string]: unknown;
  };
}

/**
 * API key status (without revealing actual keys).
 */
export interface APIKeyStatus {
  openai_configured: boolean;
  anthropic_configured: boolean;
  google_configured: boolean;
}

/**
 * Fetch all settings from the backend.
 */
export async function fetchSettings(): Promise<Settings> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/settings`);

  if (!response.ok) {
    throw new Error(`Failed to fetch settings: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get API key configuration status.
 */
export async function fetchAPIKeyStatus(): Promise<APIKeyStatus> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/settings/api-keys/status`);

  if (!response.ok) {
    throw new Error(`Failed to fetch API key status: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Update an API key.
 */
export async function updateAPIKey(
  provider: 'openai' | 'anthropic' | 'google',
  apiKey: string
): Promise<{ success: boolean; message: string }> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/settings/api-keys`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      provider,
      api_key: apiKey,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || `Failed to update API key: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Update model selection for a component.
 */
export async function updateModel(
  component: 'master_agent' | 'crew_coder' | 'autogen_auditor',
  modelName: string
): Promise<{ success: boolean; message: string }> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/settings/models`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      component,
      model_name: modelName,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || `Failed to update model: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Update a user preference.
 */
export async function updatePreference(
  key: string,
  value: unknown
): Promise<{ success: boolean; message: string }> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/settings/preferences`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      key,
      value,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || `Failed to update preference: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Reset all settings to defaults.
 */
export async function resetSettings(): Promise<{ success: boolean; message: string }> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/settings/reset`, {
    method: 'POST',
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || `Failed to reset settings: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get the config file path (for debugging).
 */
export async function getConfigPath(): Promise<string> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/settings/config-path`);

  if (!response.ok) {
    throw new Error(`Failed to get config path: ${response.statusText}`);
  }

  const data = await response.json();
  return data.config_path;
}

// ============================================================================
// Usage Statistics
// ============================================================================

/**
 * Model-level usage breakdown.
 */
export interface ModelUsage {
  model: string;
  tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  cost_usd: number;
  call_count: number;
}

/**
 * Session usage statistics.
 */
export interface UsageStatistics {
  total_calls: number;
  total_tokens: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_cost_usd: number;
  by_model: ModelUsage[];
}

/**
 * Fetch current session usage statistics.
 */
export async function fetchUsageStatistics(): Promise<UsageStatistics> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/settings/usage`);

  if (!response.ok) {
    throw new Error(`Failed to fetch usage statistics: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Reset session usage statistics.
 */
export async function resetUsageStatistics(): Promise<{ success: boolean; message: string }> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/settings/usage/reset`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error(`Failed to reset usage statistics: ${response.statusText}`);
  }

  return response.json();
}

// ============================================================================
// Tool Analytics
// ============================================================================

/**
 * Tool usage statistics.
 */
export interface ToolStats {
  calls: number;
  successes: number;
  failures: number;
  success_rate: number;
  avg_duration_ms: number;
  total_duration_ms: number;
}

/**
 * Tool analytics summary.
 */
export interface ToolAnalytics {
  total_calls: number;
  total_successes: number;
  total_failures: number;
  overall_success_rate: number;
  by_tool: Record<string, ToolStats>;
  slow_tools: string[];
  failing_tools: string[];
}

/**
 * Fetch tool usage analytics.
 */
export async function fetchToolAnalytics(projectRoot?: string): Promise<ToolAnalytics> {
  const baseUrl = await getBaseUrl();
  const params = projectRoot ? `?project_root=${encodeURIComponent(projectRoot)}` : '';
  const response = await fetch(`${baseUrl}/settings/analytics${params}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch tool analytics: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Reset tool usage analytics.
 */
export async function resetToolAnalytics(projectRoot?: string): Promise<{ success: boolean; message: string }> {
  const baseUrl = await getBaseUrl();
  const params = projectRoot ? `?project_root=${encodeURIComponent(projectRoot)}` : '';
  const response = await fetch(`${baseUrl}/settings/analytics/reset${params}`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error(`Failed to reset tool analytics: ${response.statusText}`);
  }

  return response.json();
}
