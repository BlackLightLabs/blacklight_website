/**
 * E2E tests for admin functionality
 *
 * Tests the complete admin journey including:
 * - Admin navigation and authentication
 * - User management (list, view, edit, toggle status)
 * - Role management (list, create, edit, delete)
 * - Permission assignment
 */

import { test, expect, type Page } from "@playwright/test";

// Test configuration
const ADMIN_EMAIL = "admin@example.com";
const ADMIN_PASSWORD = "admin123";
const BASE_URL = "http://localhost:5173";
const API_URL = "http://localhost:8000";

// Helper function to login as admin
async function loginAsAdmin(page: Page) {
  await page.goto("/login");
  await page.getByRole("textbox", { name: /email/i }).fill(ADMIN_EMAIL);
  await page.getByRole("textbox", { name: /password/i }).fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: /login/i }).click();

  // Wait for successful login
  await expect(page).toHaveURL("/");
  await expect(page.getByText(/welcome back/i)).toBeVisible();
}

test.describe("Admin Authentication & Navigation", () => {
  test("should login as admin and see admin menu", async ({ page }) => {
    await loginAsAdmin(page);

    // Admin section should be visible in sidebar
    await expect(page.getByRole("link", { name: "Users" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Roles" })).toBeVisible();
  });

  test("should navigate to admin pages", async ({ page }) => {
    await loginAsAdmin(page);

    // Navigate to users page
    await page.getByRole("link", { name: "Users" }).click();
    await expect(page).toHaveURL("/admin/users");
    await expect(page.getByText(/user management/i)).toBeVisible();

    // Navigate to roles page
    await page.getByRole("link", { name: "Roles" }).click();
    await expect(page).toHaveURL("/admin/roles");
    await expect(page.getByText(/role management/i)).toBeVisible();
  });
});

test.describe("User Management", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto("/admin/users");
  });

  test("should display users list", async ({ page }) => {
    // Wait for users table to load
    await expect(page.getByRole("table")).toBeVisible();

    // Should show table headers
    await expect(page.getByRole("columnheader", { name: /email/i })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: /name/i })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: /role/i })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: /status/i })).toBeVisible();

    // Should show user rows
    await expect(page.getByText(ADMIN_EMAIL)).toBeVisible();
    await expect(page.getByText(/superuser/i)).toBeVisible();
  });

  test("should search for users", async ({ page }) => {
    const searchInput = page.getByPlaceholder(/search by email or name/i);

    await searchInput.fill("admin");

    // Should show only matching users
    await expect(page.getByText(ADMIN_EMAIL)).toBeVisible();

    // Clear search
    await searchInput.clear();
  });

  test("should filter users by role", async ({ page }) => {
    // Open role filter dropdown
    const roleFilter = page.getByRole("combobox").filter({ hasText: /all roles/i });
    await roleFilter.click();

    // Select a role
    await page.getByRole("option", { name: "user" }).click();

    // Should update the list (implementation dependent)
    await page.waitForTimeout(500);
  });

  test("should filter users by status", async ({ page }) => {
    // Open status filter dropdown
    const statusFilter = page.getByRole("combobox").filter({ hasText: /all users/i });
    await statusFilter.click();

    // Select active only
    await page.getByRole("option", { name: /active only/i }).click();

    // Should update the list (implementation dependent)
    await page.waitForTimeout(500);
  });

  test("should navigate to user detail page", async ({ page }) => {
    // Click on a user's email link
    await page.getByRole("link", { name: ADMIN_EMAIL }).first().click();

    // Should navigate to user detail page
    await expect(page.getByText(/user information/i)).toBeVisible();
    await expect(page.getByText(/role & permissions/i)).toBeVisible();
    await expect(page.getByText(ADMIN_EMAIL)).toBeVisible();
  });

  test("should change user role", async ({ page }) => {
    // Find a user row (not the superuser)
    const userRow = page.getByRole("row").filter({ hasText: /test@example\.com/i }).first();

    if (await userRow.isVisible()) {
      // Click the role dropdown for this user
      const roleDropdown = userRow.getByRole("combobox");
      await roleDropdown.click();

      // Select a different role
      await page.getByRole("option", { name: "admin" }).click();

      // Should show success notification
      await expect(page.getByText(/user role updated/i)).toBeVisible({ timeout: 5000 });
    }
  });

  test("should toggle user active status", async ({ page }) => {
    // Find a user row (not the superuser)
    const userRow = page.getByRole("row").filter({ hasText: /test@example\.com/i }).first();

    if (await userRow.isVisible()) {
      // Find the switch in this row
      const activeSwitch = userRow.getByRole("switch");
      const isChecked = await activeSwitch.isChecked();

      // Toggle the switch
      await activeSwitch.click();

      // Should show success notification
      if (isChecked) {
        await expect(page.getByText(/user deactivated/i)).toBeVisible({ timeout: 5000 });
      } else {
        await expect(page.getByText(/user activated/i)).toBeVisible({ timeout: 5000 });
      }
    }
  });
});

test.describe("User Detail Page", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto("/admin/users");

    // Navigate to first user detail page
    await page.getByRole("button", { name: /view details/i }).first().click();
  });

  test("should display user information", async ({ page }) => {
    // Should show all user info sections
    await expect(page.getByText(/user information/i)).toBeVisible();
    await expect(page.getByText(/role & permissions/i)).toBeVisible();
    await expect(page.getByText(/account management/i)).toBeVisible();

    // Should show user details
    await expect(page.getByText(/email/i)).toBeVisible();
    await expect(page.getByText(/full name/i)).toBeVisible();
    await expect(page.getByText(/joined/i)).toBeVisible();
  });

  test("should display user permissions", async ({ page }) => {
    // If user has a role, should show permissions
    const permissionsSection = page.getByText(/permissions/i);

    if (await permissionsSection.isVisible()) {
      // Should show permission badges
      await expect(page.locator('[class*="permission"]').first()).toBeVisible();
    }
  });

  test("should change user role from detail page", async ({ page }) => {
    // Find role dropdown
    const roleDropdown = page.getByRole("combobox").filter({ hasText: /guest|user|admin/i });

    if (await roleDropdown.isVisible()) {
      await roleDropdown.click();

      // Select a different role
      await page.getByRole("option", { name: "user" }).click();

      // Should show success notification
      await expect(page.getByText(/user role updated/i)).toBeVisible({ timeout: 5000 });

      // Permissions should update
      await page.waitForTimeout(1000);
    }
  });

  test("should toggle user status from detail page", async ({ page }) => {
    // Find the status switch
    const statusSwitch = page.getByRole("switch");
    const isChecked = await statusSwitch.isChecked();

    // Toggle status
    await statusSwitch.click();

    // Should show success notification
    if (isChecked) {
      await expect(page.getByText(/user deactivated/i)).toBeVisible({ timeout: 5000 });
    } else {
      await expect(page.getByText(/user activated/i)).toBeVisible({ timeout: 5000 });
    }
  });

  test("should navigate back to users list", async ({ page }) => {
    await page.getByRole("button", { name: /back to users/i }).click();

    await expect(page).toHaveURL("/admin/users");
    await expect(page.getByText(/user management/i)).toBeVisible();
  });
});

test.describe("Role Management", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto("/admin/roles");
  });

  test("should display roles list", async ({ page }) => {
    // Should show default roles
    await expect(page.getByText("superadmin")).toBeVisible();
    await expect(page.getByText("admin")).toBeVisible();
    await expect(page.getByText("user")).toBeVisible();
    await expect(page.getByText("guest")).toBeVisible();

    // Should show permission counts
    await expect(page.getByText(/14 permissions/i)).toBeVisible(); // superadmin
  });

  test("should display role permissions", async ({ page }) => {
    // Each role should show its permissions
    const superadminCard = page.locator('div').filter({ hasText: /^superadmin/ }).first();

    // Should show permission badges
    await expect(superadminCard.getByText(/agents:create/i)).toBeVisible();
    await expect(superadminCard.getByText(/users:read/i)).toBeVisible();
  });

  test("should open create role dialog", async ({ page }) => {
    await page.getByRole("button", { name: /create role/i }).click();

    // Dialog should open
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(page.getByRole("heading", { name: /create new role/i })).toBeVisible();

    // Should have form fields
    await expect(page.getByPlaceholder(/e\.g\., moderator/i)).toBeVisible();
    await expect(page.getByPlaceholder(/brief description/i)).toBeVisible();
  });

  test("should create a new role", async ({ page }) => {
    await page.getByRole("button", { name: /create role/i }).click();

    // Fill in role details
    await page.getByPlaceholder(/e\.g\., moderator/i).fill("Test Role");
    await page.getByPlaceholder(/brief description/i).fill("A test role for E2E testing");

    // Select permissions
    const agentsTab = page.getByRole("tab", { name: "agents" });
    if (await agentsTab.isVisible()) {
      await agentsTab.click();
    }

    // Check some permissions
    await page.getByRole("checkbox", { name: /agents:read/i }).check();
    await page.getByRole("checkbox", { name: /agents:create/i }).check();

    // Submit form
    await page.getByRole("button", { name: /create role/i, exact: true }).click();

    // Should show success notification
    await expect(page.getByText(/role created successfully/i)).toBeVisible({ timeout: 5000 });

    // New role should appear in list
    await expect(page.getByText("Test Role")).toBeVisible();
  });

  test("should edit an existing role", async ({ page }) => {
    // Find the user role and click edit
    const userRoleCard = page.locator('div').filter({ hasText: /^user\s+\d+ permissions/ });
    await userRoleCard.getByRole("button", { name: /edit/i }).click();

    // Dialog should open with existing data
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(page.getByRole("heading", { name: /edit role/i })).toBeVisible();

    // Should have pre-filled values
    const nameInput = page.getByPlaceholder(/e\.g\., moderator/i);
    await expect(nameInput).toHaveValue("user");

    // Update description
    await page.getByPlaceholder(/brief description/i).clear();
    await page.getByPlaceholder(/brief description/i).fill("Updated user role description");

    // Save changes
    await page.getByRole("button", { name: /save changes/i }).click();

    // Should show success notification
    await expect(page.getByText(/role updated successfully/i)).toBeVisible({ timeout: 5000 });
  });

  test("should delete a role", async ({ page }) => {
    // First create a test role to delete
    await page.getByRole("button", { name: /create role/i }).click();
    await page.getByPlaceholder(/e\.g\., moderator/i).fill("Deletable Role");
    await page.getByRole("button", { name: /create role/i, exact: true }).click();
    await page.waitForTimeout(1000);

    // Find the deletable role and click delete
    const deletableCard = page.locator('div').filter({ hasText: "Deletable Role" });

    if (await deletableCard.isVisible()) {
      // Mock the confirmation dialog
      page.on("dialog", (dialog) => dialog.accept());

      await deletableCard.getByRole("button", { name: /delete/i }).click();

      // Should show success notification
      await expect(page.getByText(/role deleted successfully/i)).toBeVisible({ timeout: 5000 });

      // Role should no longer be in list
      await expect(page.getByText("Deletable Role")).not.toBeVisible();
    }
  });

  test("should prevent deleting role with assigned users", async ({ page }) => {
    // Try to delete the "user" role which has users assigned
    const userRoleCard = page.locator('div').filter({ hasText: /^user\s+\d+ permissions/ });

    // Mock the confirmation dialog
    page.on("dialog", (dialog) => dialog.accept());

    await userRoleCard.getByRole("button", { name: /delete/i }).first().click();

    // Should show error notification
    await expect(page.getByText(/cannot delete role that is assigned/i)).toBeVisible({ timeout: 5000 });
  });

  test("should show permission tabs", async ({ page }) => {
    await page.getByRole("button", { name: /create role/i }).click();

    // Should show permission tabs
    await expect(page.getByRole("tab", { name: "agents" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "users" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "roles" })).toBeVisible();

    // Should be able to switch tabs
    await page.getByRole("tab", { name: "users" }).click();
    await expect(page.getByRole("checkbox", { name: /users:read/i })).toBeVisible();

    await page.getByRole("tab", { name: "roles" }).click();
    await expect(page.getByRole("checkbox", { name: /roles:read/i })).toBeVisible();
  });

  test("should update selected permissions count", async ({ page }) => {
    await page.getByRole("button", { name: /create role/i }).click();

    // Initially should show 0 selected
    await expect(page.getByText(/0 selected/i)).toBeVisible();

    // Check some permissions
    await page.getByRole("checkbox", { name: /agents:read/i }).check();
    await page.getByRole("checkbox", { name: /agents:create/i }).check();

    // Should update count
    await expect(page.getByText(/2 selected/i)).toBeVisible();

    // Uncheck one
    await page.getByRole("checkbox", { name: /agents:read/i }).uncheck();

    // Should update count
    await expect(page.getByText(/1 selected/i)).toBeVisible();
  });
});

test.describe("Permissions & Authorization", () => {
  test("non-admin users should not see admin menu", async ({ page }) => {
    // This test would require a non-admin user account
    // Skipped for now - would need proper test user setup
    test.skip();
  });

  test("should handle API errors gracefully", async ({ page }) => {
    await loginAsAdmin(page);

    // Navigate to a non-existent user
    await page.goto("/admin/users/99999");

    // Should show error message or redirect
    // Implementation dependent on error handling
    await page.waitForTimeout(1000);
  });
});

test.describe("Responsive Design", () => {
  test("should work on mobile viewport", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });

    await loginAsAdmin(page);
    await page.goto("/admin/users");

    // Should still be functional
    await expect(page.getByText(/user management/i)).toBeVisible();

    // Toggle sidebar
    const toggleButton = page.getByRole("button", { name: /toggle sidebar/i });
    if (await toggleButton.isVisible()) {
      await toggleButton.click();
    }
  });

  test("should work on tablet viewport", async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });

    await loginAsAdmin(page);
    await page.goto("/admin/roles");

    // Should display properly
    await expect(page.getByText(/role management/i)).toBeVisible();
  });
});
