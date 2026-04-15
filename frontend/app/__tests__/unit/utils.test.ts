/**
 * Unit tests for utility functions
 */

import { describe, it, expect } from "vitest";
import { cn } from "../../lib/utils";

describe("Utils", () => {
  describe("cn (className merger)", () => {
    it("should merge single class", () => {
      expect(cn("text-red-500")).toBe("text-red-500");
    });

    it("should merge multiple classes", () => {
      expect(cn("text-red-500", "bg-blue-500")).toContain("text-red-500");
      expect(cn("text-red-500", "bg-blue-500")).toContain("bg-blue-500");
    });

    it("should handle conditional classes", () => {
      const isActive = true;
      const result = cn("base-class", isActive && "active-class");
      expect(result).toContain("base-class");
      expect(result).toContain("active-class");
    });

    it("should handle false/null/undefined values", () => {
      expect(cn("valid", false, null, undefined, "also-valid")).toBe("valid also-valid");
    });

    it("should override conflicting Tailwind classes", () => {
      // twMerge should handle Tailwind class conflicts
      const result = cn("px-2 py-1", "px-4");
      expect(result).toContain("px-4");
      expect(result).not.toContain("px-2");
    });
  });
});
