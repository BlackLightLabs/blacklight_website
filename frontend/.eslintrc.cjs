/**
 * ESLint Configuration for Agent Builder Frontend
 *
 * Rules enforce:
 * - No console.log statements in production code
 * - TypeScript best practices
 * - React/JSX best practices
 * - Accessibility standards
 */

module.exports = {
  root: true,
  env: {
    browser: true,
    es2022: true,
    node: true,
  },
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react/recommended",
    "plugin:react-hooks/recommended",
    "plugin:jsx-a11y/recommended",
  ],
  parser: "@typescript-eslint/parser",
  parserOptions: {
    ecmaVersion: "latest",
    sourceType: "module",
    ecmaFeatures: {
      jsx: true,
    },
  },
  plugins: ["@typescript-eslint", "react", "react-hooks", "jsx-a11y"],
  settings: {
    react: {
      version: "detect",
    },
  },
  rules: {
    // Prevent console.log in production code
    "no-console": [
      "error",
      {
        allow: ["warn", "error"], // Allow console.warn and console.error
      },
    ],

    // TypeScript-specific rules
    "@typescript-eslint/no-unused-vars": [
      "error",
      {
        argsIgnorePattern: "^_",
        varsIgnorePattern: "^_",
      },
    ],
    "@typescript-eslint/no-explicit-any": "warn", // Warn on 'any' usage
    "@typescript-eslint/explicit-module-boundary-types": "off",
    "@typescript-eslint/no-non-null-assertion": "warn",

    // React-specific rules
    "react/react-in-jsx-scope": "off", // Not needed with React 17+
    "react/prop-types": "off", // Using TypeScript for prop validation
    "react-hooks/rules-of-hooks": "error",
    "react-hooks/exhaustive-deps": "warn",

    // General code quality
    "prefer-const": "error",
    "no-var": "error",
    eqeqeq": ["error", "always"],

    // Accessibility
    "jsx-a11y/anchor-is-valid": "warn",
  },
  overrides: [
    {
      // Allow console in test files
      files: ["**/__tests__/**/*", "**/*.test.*", "**/*.spec.*"],
      rules: {
        "no-console": "off",
      },
    },
  ],
};
