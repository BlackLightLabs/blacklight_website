/**
 * E2E tests for agent creation flow
 *
 * Tests the complete user journey from creating an agent through conversation
 * to viewing the created agent.
 */

import { test, expect } from '@playwright/test'

test.describe('Agent Creation Flow', () => {
  test('should create agent through conversation', async ({ page }) => {
    // Navigate to agent creation page
    await page.goto('/create-agent')

    // Should show initial assistant message
    await expect(page.getByText(/Hi! I'm here to help you build/i)).toBeVisible()

    // Type and send a message
    const chatInput = page.getByPlaceholder(/message agent builder/i)
    await chatInput.fill('I want an agent that checks my email for sales leads')
    await chatInput.press('Enter')

    // Should show user message
    await expect(page.getByText('I want an agent that checks my email')).toBeVisible()

    // Wait for streaming response (mock or real backend needed)
    // In real test, you'd mock the API or have test backend
    await page.waitForTimeout(1000)

    // Should be able to continue conversation
    await chatInput.fill('Yes, that sounds good')
    await chatInput.press('Enter')
  })

  test('should navigate to created agent', async ({ page }) => {
    // This test would require mocking the backend or using a test database
    // For now, we test the navigation flow

    await page.goto('/agents')
    await expect(page.getByRole('heading', { name: /agents/i })).toBeVisible()
  })

  test('should handle network errors gracefully', async ({ page }) => {
    // Intercept and fail the API call
    await page.route('**/api/agents/chat/stream', route => {
      route.abort('failed')
    })

    await page.goto('/create-agent')

    const chatInput = page.getByPlaceholder(/message agent builder/i)
    await chatInput.fill('Test message')
    await chatInput.press('Enter')

    // Should show error toast or error message
    await page.waitForTimeout(1000)
    // You would assert on error message here
  })
})

test.describe('Agents List Page', () => {
  test('should display agents list', async ({ page }) => {
    await page.goto('/agents')

    // Page should load
    await expect(page.getByRole('heading')).toBeVisible()
  })
})
