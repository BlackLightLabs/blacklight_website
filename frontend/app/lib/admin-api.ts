/**
 * Admin API Client
 *
 * Handles admin operations for user and role management.
 * All endpoints require superuser or specific admin permissions.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// ============================================================================
// Types
// ============================================================================

export interface Permission {
  id: number;
  name: string;
  resource: string;
  action: string;
  description?: string;
  created_at: string;
}

export interface Role {
  id: number;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface RoleWithPermissions extends Role {
  permissions: Permission[];
}

export interface UserListItem {
  id: number;
  email: string;
  full_name?: string;
  role_id?: number;
  role_name?: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
  last_login_at?: string;
  created_at: string;
}

export interface UserWithRole {
  id: number;
  email: string;
  full_name?: string;
  role_id?: number;
  role?: Role;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
  last_login_at?: string;
}

export interface UserFilters {
  skip?: number;
  limit?: number;
  search?: string;
  role_id?: number;
  is_active?: boolean;
}

export interface RoleCreateRequest {
  name: string;
  description?: string;
  permission_ids?: number[];
}

export interface RoleUpdateRequest {
  name?: string;
  description?: string;
  permission_ids?: number[];
}

export interface UpdateUserRoleRequest {
  role_id: number;
}

// ============================================================================
// Helper Functions
// ============================================================================

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// ============================================================================
// User Management API
// ============================================================================

export const adminUserApi = {
  /**
   * List all users with optional filtering
   */
  async listUsers(filters?: UserFilters): Promise<UserListItem[]> {
    const params = new URLSearchParams();

    if (filters?.skip !== undefined) params.append("skip", filters.skip.toString());
    if (filters?.limit !== undefined) params.append("limit", filters.limit.toString());
    if (filters?.search) params.append("search", filters.search);
    if (filters?.role_id !== undefined) params.append("role_id", filters.role_id.toString());
    if (filters?.is_active !== undefined) params.append("is_active", filters.is_active.toString());

    const response = await fetch(`${API_BASE_URL}/api/admin/users?${params}`, {
      method: "GET",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
    });

    return handleResponse<UserListItem[]>(response);
  },

  /**
   * Get detailed information about a specific user
   */
  async getUserDetails(userId: number): Promise<UserWithRole> {
    const response = await fetch(`${API_BASE_URL}/api/admin/users/${userId}`, {
      method: "GET",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
    });

    return handleResponse<UserWithRole>(response);
  },

  /**
   * Update a user's role
   */
  async updateUserRole(userId: number, roleId: number): Promise<UserWithRole> {
    const response = await fetch(`${API_BASE_URL}/api/admin/users/${userId}/role`, {
      method: "PATCH",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ role_id: roleId }),
    });

    return handleResponse<UserWithRole>(response);
  },

  /**
   * Activate a user account
   */
  async activateUser(userId: number): Promise<UserWithRole> {
    const response = await fetch(`${API_BASE_URL}/api/admin/users/${userId}/activate`, {
      method: "PATCH",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
    });

    return handleResponse<UserWithRole>(response);
  },

  /**
   * Deactivate a user account
   */
  async deactivateUser(userId: number): Promise<UserWithRole> {
    const response = await fetch(`${API_BASE_URL}/api/admin/users/${userId}/deactivate`, {
      method: "PATCH",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
    });

    return handleResponse<UserWithRole>(response);
  },
};

// ============================================================================
// Role Management API
// ============================================================================

export const adminRoleApi = {
  /**
   * List all roles with their permissions
   */
  async listRoles(): Promise<RoleWithPermissions[]> {
    const response = await fetch(`${API_BASE_URL}/api/admin/roles`, {
      method: "GET",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
    });

    return handleResponse<RoleWithPermissions[]>(response);
  },

  /**
   * Get detailed information about a specific role
   */
  async getRoleDetails(roleId: number): Promise<RoleWithPermissions> {
    const response = await fetch(`${API_BASE_URL}/api/admin/roles/${roleId}`, {
      method: "GET",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
    });

    return handleResponse<RoleWithPermissions>(response);
  },

  /**
   * Create a new role
   */
  async createRole(roleData: RoleCreateRequest): Promise<RoleWithPermissions> {
    const response = await fetch(`${API_BASE_URL}/api/admin/roles`, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(roleData),
    });

    return handleResponse<RoleWithPermissions>(response);
  },

  /**
   * Update an existing role
   */
  async updateRole(roleId: number, roleData: RoleUpdateRequest): Promise<RoleWithPermissions> {
    const response = await fetch(`${API_BASE_URL}/api/admin/roles/${roleId}`, {
      method: "PATCH",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(roleData),
    });

    return handleResponse<RoleWithPermissions>(response);
  },

  /**
   * Delete a role
   */
  async deleteRole(roleId: number): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/admin/roles/${roleId}`, {
      method: "DELETE",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
    });

    return handleResponse<void>(response);
  },

  /**
   * Add a permission to a role
   */
  async addPermissionToRole(roleId: number, permissionId: number): Promise<RoleWithPermissions> {
    const response = await fetch(
      `${API_BASE_URL}/api/admin/roles/${roleId}/permissions/${permissionId}`,
      {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
      },
    );

    return handleResponse<RoleWithPermissions>(response);
  },

  /**
   * Remove a permission from a role
   */
  async removePermissionFromRole(
    roleId: number,
    permissionId: number,
  ): Promise<RoleWithPermissions> {
    const response = await fetch(
      `${API_BASE_URL}/api/admin/roles/${roleId}/permissions/${permissionId}`,
      {
        method: "DELETE",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
      },
    );

    return handleResponse<RoleWithPermissions>(response);
  },
};

// ============================================================================
// Permission Management API
// ============================================================================

export const adminPermissionApi = {
  /**
   * List all permissions
   */
  async listPermissions(resource?: string): Promise<Permission[]> {
    const params = new URLSearchParams();
    if (resource) params.append("resource", resource);

    const response = await fetch(`${API_BASE_URL}/api/admin/permissions?${params}`, {
      method: "GET",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
    });

    return handleResponse<Permission[]>(response);
  },
};

// Export combined admin API
export const adminApi = {
  users: adminUserApi,
  roles: adminRoleApi,
  permissions: adminPermissionApi,
};
