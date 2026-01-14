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
  provider: 'openai' | 'anthropic',
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
