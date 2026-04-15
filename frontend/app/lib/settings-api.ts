/**
 * Settings API Client
 *
 * Handles user settings operations with FastAPI backend using httpOnly cookies.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface UserSettings {
  id: number;
  user_id: number;
  theme: "light" | "dark" | "system";
  custom_prompts?: Record<string, any>;
  preferences?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface SettingsUpdate {
  theme?: "light" | "dark" | "system";
  custom_prompts?: Record<string, any>;
  preferences?: Record<string, any>;
}

export const settingsApi = {
  /**
   * Get current user's settings
   */
  async getMySettings(): Promise<UserSettings> {
    const response = await fetch(`${API_BASE_URL}/api/settings/me`, {
      credentials: "include",
    });

    if (!response.ok) {
      throw new Error("Failed to fetch settings");
    }

    return response.json();
  },

  /**
   * Update current user's settings
   */
  async updateMySettings(settings: SettingsUpdate): Promise<UserSettings> {
    const response = await fetch(`${API_BASE_URL}/api/settings/me`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(settings),
      credentials: "include",
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to update settings");
    }

    return response.json();
  },

  /**
   * Update current user's theme preference
   */
  async updateTheme(theme: "light" | "dark" | "system"): Promise<UserSettings> {
    const response = await fetch(`${API_BASE_URL}/api/settings/me/theme?theme=${theme}`, {
      method: "PATCH",
      credentials: "include",
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to update theme");
    }

    return response.json();
  },
};
