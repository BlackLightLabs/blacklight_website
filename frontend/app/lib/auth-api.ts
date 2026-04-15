/**
 * Authentication API Client
 *
 * Handles authentication with FastAPI backend using httpOnly cookies.
 * Uses FastAPI-Users endpoints for registration, login, and logout.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface User {
  id: number;
  email: string;
  full_name?: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
  role?: {
    id: number;
    name: string;
  };
}

export interface LoginRequest {
  username: string; // FastAPI-Users uses "username" for email
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name?: string;
}

export interface AuthError {
  detail: string;
}

export interface OAuthProvider {
  name: string;
  display_name: string;
  enabled: boolean;
  authorize_url: string;
}

export interface OAuthProvidersResponse {
  enabled: boolean;
  providers: OAuthProvider[];
}

export interface ConnectedOAuthAccount {
  id: number;
  provider: string;
  display_name: string;
  account_email: string;
  connected_at: string;
}

export interface ConnectedAccountsResponse {
  accounts: ConnectedOAuthAccount[];
  available_providers: OAuthProvider[];
}

export const authApi = {
  /**
   * Login with email and password
   * Sets httpOnly cookie on success
   */
  async login(email: string, password: string): Promise<void> {
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    const response = await fetch(`${API_BASE_URL}/api/auth/jwt/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: formData.toString(),
      credentials: "include", // Important: include cookies
    });

    if (!response.ok) {
      const error: AuthError = await response.json();
      throw new Error(error.detail || "Login failed");
    }

    // FastAPI-Users login endpoint returns 204 No Content (httpOnly cookie set)
    // No need to parse response body
  },

  /**
   * Register a new user
   */
  async register(data: RegisterRequest): Promise<User> {
    const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
      credentials: "include",
    });

    if (!response.ok) {
      const error: AuthError = await response.json();
      throw new Error(error.detail || "Registration failed");
    }

    return response.json();
  },

  /**
   * Logout current user
   * Clears httpOnly cookie
   */
  async logout(): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/auth/jwt/logout`, {
      method: "POST",
      credentials: "include",
    });

    if (!response.ok) {
      throw new Error("Logout failed");
    }
  },

  /**
   * Get current user
   * Uses cookie-based authentication
   */
  async getCurrentUser(): Promise<User | null> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/users/me`, {
        credentials: "include",
      });

      if (response.status === 401) {
        return null;
      }

      if (!response.ok) {
        throw new Error("Failed to fetch user");
      }

      return response.json();
    } catch (error) {
      console.error("Failed to get current user:", error);
      return null;
    }
  },

  /**
   * Update current user
   */
  async updateUser(data: Partial<User>): Promise<User> {
    const response = await fetch(`${API_BASE_URL}/api/users/me`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
      credentials: "include",
    });

    if (!response.ok) {
      const error: AuthError = await response.json();
      throw new Error(error.detail || "Update failed");
    }

    return response.json();
  },

  /**
   * Get available OAuth providers
   * Returns list of enabled OAuth providers (Google, GitHub, Microsoft, etc.)
   */
  async getOAuthProviders(): Promise<OAuthProvidersResponse> {
    const response = await fetch(`${API_BASE_URL}/api/auth/oauth/providers`, {
      credentials: "include",
    });

    if (!response.ok) {
      throw new Error("Failed to fetch OAuth providers");
    }

    return response.json();
  },

  /**
   * Initiate OAuth login flow for a provider (e.g., "google", "github")
   *
   * FastAPI-Users OAuth Flow:
   * 1. Frontend fetches /authorize → backend returns JSON with authorization_url
   * 2. Frontend redirects to authorization_url (GitHub's OAuth page)
   * 3. User authorizes on GitHub
   * 4. GitHub redirects to backend /callback with authorization code
   * 5. Backend exchanges code for token, creates/logs in user, sets httpOnly cookie
   * 6. Backend redirects to redirect_url (frontend success page)
   * 7. User is authenticated with cookie
   */
  async initiateOAuthLogin(provider: string): Promise<void> {
    // Fetch authorization URL from backend
    const response = await fetch(`${API_BASE_URL}/api/auth/${provider}/authorize`, {
      credentials: "include",
    });

    if (!response.ok) {
      throw new Error("Failed to initiate OAuth flow");
    }

    const data = await response.json();

    // Redirect browser to OAuth provider's authorization page
    window.location.href = data.authorization_url;
  },

  /**
   * Get connected OAuth accounts for current user
   * Returns list of OAuth providers linked to the user's account
   */
  async getConnectedAccounts(): Promise<ConnectedAccountsResponse> {
    const response = await fetch(`${API_BASE_URL}/api/auth/oauth/accounts`, {
      credentials: "include",
    });

    if (!response.ok) {
      throw new Error("Failed to fetch connected accounts");
    }

    return response.json();
  },

  /**
   * Disconnect an OAuth account
   * Removes the link between user account and OAuth provider
   */
  async disconnectOAuthAccount(accountId: number): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/auth/oauth/accounts/${accountId}`, {
      method: "DELETE",
      credentials: "include",
    });

    if (!response.ok) {
      const error: AuthError = await response.json();
      throw new Error(error.detail || "Failed to disconnect OAuth account");
    }
  },
};
