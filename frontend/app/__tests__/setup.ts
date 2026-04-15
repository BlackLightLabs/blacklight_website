/**
 * Test setup file for Vitest
 *
 * This file is automatically loaded before each test file.
 * It sets up the testing environment and provides global utilities.
 */

import { expect, afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import * as matchers from "@testing-library/jest-dom/matchers";

// Extend Vitest's expect with jest-dom matchers
expect.extend(matchers);

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Mock environment variables
process.env.VITE_API_URL = "http://localhost:8000";

// Global test utilities
global.fetch = global.fetch || (() => Promise.resolve({} as Response));
