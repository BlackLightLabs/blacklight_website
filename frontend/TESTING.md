# Frontend Testing Guide

This guide explains how to write and run tests for the Agent Builder frontend.

---

## Table of Contents

- [Overview](#overview)
- [Test Types](#test-types)
- [Running Tests](#running-tests)
- [Writing Unit Tests](#writing-unit-tests)
- [Writing E2E Tests](#writing-e2e-tests)
- [Test Organization](#test-organization)
- [Best Practices](#best-practices)
- [Coverage Requirements](#coverage-requirements)
- [Troubleshooting](#troubleshooting)

---

## Overview

The frontend uses:
- **Vitest** for unit/integration tests
- **React Testing Library** for component testing
- **Playwright** for E2E tests
- **MSW (Mock Service Worker)** for API mocking

---

## Test Types

### Unit Tests
Test individual components or functions in isolation.

**Location**: `app/__tests__/unit/`

**Example**:
```typescript
// app/__tests__/unit/chat-input.test.tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChatInput } from "~/components/chat-input";

describe("ChatInput", () => {
  it("should render with placeholder", () => {
    render(<ChatInput onSend={vi.fn()} />);
    expect(screen.getByPlaceholderText("Type your message...")).toBeInTheDocument();
  });
});
```

### Integration Tests
Test how multiple components work together or API integrations.

**Location**: `app/__tests__/integration/`

**Example**:
```typescript
// app/__tests__/integration/agent-creation-flow.test.tsx
import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CreateAgentPage } from "~/routes/create-agent";

describe("Agent Creation Flow", () => {
  it("should create agent through conversation", async () => {
    const user = userEvent.setup();
    render(<CreateAgentPage />);

    const input = screen.getByPlaceholderText("Type your message...");
    await user.type(input, "Create a calculator agent");
    await user.keyboard("{Enter}");

    await waitFor(() => {
      expect(screen.getByText(/agent created/i)).toBeInTheDocument();
    });
  });
});
```

### End-to-End Tests
Test complete user workflows through the browser.

**Location**: `e2e/`

**Example**:
```typescript
// e2e/agent-creation.spec.ts
import { test, expect } from "@playwright/test";

test("user can create an agent", async ({ page }) => {
  await page.goto("/create-agent");
  await page.fill('textarea[placeholder="Type your message..."]', "Create a weather agent");
  await page.press('textarea[placeholder="Type your message..."]', "Enter");

  await expect(page.locator("text=Agent created successfully")).toBeVisible();
});
```

---

## Running Tests

### Unit Tests

```bash
# Watch mode (for development)
npm run test

# Run once (for CI)
npm run test:run

# With coverage
npm run test:coverage

# With UI
npm run test:ui
```

### E2E Tests

```bash
# Run E2E tests headless
npm run test:e2e

# Run with UI
npm run test:e2e:ui
```

### All Validation

```bash
# Run linting, type checking, and tests
npm run validate
```

---

## Writing Unit Tests

### Component Test Structure

```typescript
/**
 * Unit tests for ComponentName
 *
 * Tests cover:
 * - Rendering
 * - User interactions
 * - State management
 * - Edge cases
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ComponentName } from "~/components/component-name";

describe("ComponentName", () => {
  describe("Rendering", () => {
    it("should render with default props", () => {
      render(<ComponentName />);
      // assertions
    });
  });

  describe("User Interactions", () => {
    it("should handle button click", async () => {
      const handleClick = vi.fn();
      const user = userEvent.setup();

      render(<ComponentName onClick={handleClick} />);

      const button = screen.getByRole("button");
      await user.click(button);

      expect(handleClick).toHaveBeenCalledTimes(1);
    });
  });

  describe("State Management", () => {
    // State tests
  });

  describe("Edge Cases", () => {
    // Edge case tests
  });
});
```

### Testing Library Queries

**Priority order** (use highest priority that works):

1. **Accessible Queries** (preferred):
   - `getByRole`
   - `getByLabelText`
   - `getByPlaceholderText`
   - `getByText`

2. **Semantic Queries**:
   - `getByAltText`
   - `getByTitle`

3. **Test IDs** (last resort):
   - `getByTestId`

**Example**:
```typescript
// ✅ Good: Use accessible queries
const button = screen.getByRole("button", { name: /submit/i });
const input = screen.getByLabelText("Email");
const heading = screen.getByRole("heading", { level: 1 });

// ❌ Bad: Avoid test IDs unless necessary
const button = screen.getByTestId("submit-button");
```

### User Interactions

Always use `@testing-library/user-event` instead of `fireEvent`:

```typescript
import userEvent from "@testing-library/user-event";

// ✅ Good: userEvent (simulates real user behavior)
const user = userEvent.setup();
await user.type(input, "Hello");
await user.click(button);

// ❌ Bad: fireEvent (doesn't simulate real behavior)
fireEvent.change(input, { target: { value: "Hello" } });
fireEvent.click(button);
```

### Mocking API Calls

Use MSW (Mock Service Worker) for API mocking:

```typescript
import { rest } from "msw";
import { setupServer } from "msw/node";

const server = setupServer(
  rest.get("/api/agents", (req, res, ctx) => {
    return res(ctx.json([
      { agent_id: "1", status: "READY", description: "Test Agent" }
    ]));
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

---

## Writing E2E Tests

### E2E Test Structure

```typescript
import { test, expect } from "@playwright/test";

test.describe("Feature Name", () => {
  test.beforeEach(async ({ page }) => {
    // Setup (login, navigate, etc.)
    await page.goto("/");
  });

  test("should do something", async ({ page }) => {
    // Arrange
    await page.goto("/page");

    // Act
    await page.click("button");

    // Assert
    await expect(page.locator("text=Success")).toBeVisible();
  });
});
```

### Playwright Best Practices

```typescript
// ✅ Good: Use locators
await page.locator('button[aria-label="Submit"]').click();
await expect(page.locator("h1")).toHaveText("Welcome");

// ✅ Good: Wait for elements
await page.waitForSelector('[data-testid="agent-list"]');

// ✅ Good: Use auto-waiting assertions
await expect(page.locator(".loading")).not.toBeVisible();

// ❌ Bad: Hard-coded waits
await page.waitForTimeout(2000);
```

---

## Test Organization

### Directory Structure

```
frontend/
├── app/
│   ├── components/
│   │   ├── chat-input.tsx
│   │   └── chat-message.tsx
│   ├── __tests__/
│   │   ├── unit/
│   │   │   ├── chat-input.test.tsx
│   │   │   ├── chat-message.test.tsx
│   │   │   ├── api.test.ts
│   │   │   └── utils.test.ts
│   │   ├── integration/
│   │   │   └── agent-creation-flow.test.tsx
│   │   └── setup.ts
│   └── routes/
│       └── create-agent.tsx
├── e2e/
│   ├── agent-creation.spec.ts
│   └── admin.spec.ts
└── TESTING.md (this file)
```

### Naming Conventions

- **Test files**: `*.test.tsx` or `*.test.ts`
- **E2E files**: `*.spec.ts`
- **Setup files**: `setup.ts`

---

## Best Practices

### 1. Arrange-Act-Assert Pattern

```typescript
it("should update count on button click", async () => {
  // Arrange: Set up test environment
  const user = userEvent.setup();
  render(<Counter initialCount={0} />);

  // Act: Perform the action
  const button = screen.getByRole("button", { name: /increment/i });
  await user.click(button);

  // Assert: Verify the result
  expect(screen.getByText("Count: 1")).toBeInTheDocument();
});
```

### 2. Test Behavior, Not Implementation

```typescript
// ✅ Good: Test what the user sees
it("should display success message after submission", async () => {
  const user = userEvent.setup();
  render(<Form />);

  await user.type(screen.getByLabelText("Name"), "John");
  await user.click(screen.getByRole("button", { name: /submit/i }));

  expect(screen.getByText("Form submitted successfully")).toBeInTheDocument();
});

// ❌ Bad: Test internal state
it("should set isSubmitted to true", () => {
  const { result } = renderHook(() => useFormState());
  act(() => result.current.submit());
  expect(result.current.isSubmitted).toBe(true);
});
```

### 3. Avoid Testing Implementation Details

```typescript
// ✅ Good: Test observable behavior
expect(screen.getByText("Welcome")).toBeInTheDocument();

// ❌ Bad: Test CSS classes
expect(container.firstChild).toHaveClass("welcome-message");
```

### 4. Use Descriptive Test Names

```typescript
// ✅ Good: Describes behavior and expected result
it("should display error message when email is invalid", () => {});

// ❌ Bad: Vague or unclear
it("should work", () => {});
it("test email", () => {});
```

### 5. Keep Tests Independent

```typescript
// ✅ Good: Each test is independent
describe("UserList", () => {
  it("should display users", () => {
    render(<UserList users={mockUsers} />);
    expect(screen.getByText("John")).toBeInTheDocument();
  });

  it("should filter users", () => {
    render(<UserList users={mockUsers} filter="admin" />);
    expect(screen.queryByText("Regular User")).not.toBeInTheDocument();
  });
});

// ❌ Bad: Tests depend on each other
let currentUsers: User[];

it("should add user", () => {
  currentUsers = addUser(currentUsers, newUser);
  expect(currentUsers).toHaveLength(1);
});

it("should remove user", () => {
  // Depends on previous test!
  currentUsers = removeUser(currentUsers, newUser);
  expect(currentUsers).toHaveLength(0);
});
```

---

## Coverage Requirements

### Target Coverage

- **Statements**: > 80%
- **Branches**: > 75%
- **Functions**: > 80%
- **Lines**: > 80%

### Check Coverage

```bash
npm run test:coverage
```

Coverage report will be generated in `coverage/` directory.

### What to Test

**High Priority**:
- ✅ User-facing components
- ✅ Business logic functions
- ✅ API client methods
- ✅ Custom hooks
- ✅ Utility functions

**Low Priority**:
- ⏸️ UI components from libraries (shadcn/ui)
- ⏸️ Simple pass-through components
- ⏸️ TypeScript type definitions

---

## Troubleshooting

### Common Issues

#### 1. "Cannot find module '~/components/...'"

**Solution**: Check `vitest.config.ts` has correct path aliases:

```typescript
resolve: {
  alias: {
    "~": path.resolve(__dirname, "./app"),
  },
},
```

#### 2. "ReferenceError: fetch is not defined"

**Solution**: Add to `app/__tests__/setup.ts`:

```typescript
import { fetch, Headers, Request, Response } from "undici";

global.fetch = fetch as any;
global.Headers = Headers as any;
global.Request = Request as any;
global.Response = Response as any;
```

#### 3. Tests timeout in watch mode

**Solution**: Reduce test timeout in `vitest.config.ts`:

```typescript
test: {
  testTimeout: 10000, // 10 seconds
},
```

#### 4. "Element is not visible" in Playwright

**Solution**: Use auto-waiting:

```typescript
// Wait for element to be visible
await expect(page.locator(".modal")).toBeVisible();

// Or explicitly wait
await page.waitForSelector(".modal", { state: "visible" });
```

---

## Resources

- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [Playwright Documentation](https://playwright.dev/)
- [Testing Best Practices](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)

---

## Example Test Checklist

When writing tests for a new component, ensure you cover:

- [ ] Component renders without crashing
- [ ] Props are correctly applied
- [ ] User interactions work (clicks, typing, etc.)
- [ ] Loading states display correctly
- [ ] Error states display correctly
- [ ] Disabled states prevent interaction
- [ ] Accessibility attributes present (aria-label, role, etc.)
- [ ] Edge cases handled (empty data, long text, special characters)
- [ ] Component integrates with parent correctly

---

## Need Help?

- Check existing tests in `app/__tests__/unit/` for examples
- Review this guide for patterns and best practices
- Ask in team chat for specific testing questions
