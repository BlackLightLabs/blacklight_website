/**
 * Unit tests for ChatMessage component
 *
 * Tests cover:
 * - User message rendering
 * - Assistant message rendering
 * - System message handling
 * - Markdown rendering for assistant
 * - Avatar display
 * - CSS classes and styling
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChatMessage } from "~/components/chat-message";
import type { ChatMessage as ChatMessageType } from "~/lib/api";

describe("ChatMessage", () => {
  describe("User Messages", () => {
    const userMessage: ChatMessageType = {
      role: "user",
      content: "Hello, how can you help me?",
    };

    it("should render user message content", () => {
      render(<ChatMessage message={userMessage} />);

      expect(screen.getByText("Hello, how can you help me?")).toBeInTheDocument();
    });

    it("should display 'You' avatar for user messages", () => {
      render(<ChatMessage message={userMessage} />);

      expect(screen.getByText("You")).toBeInTheDocument();
    });

    it("should preserve whitespace in user messages", () => {
      const messageWithWhitespace: ChatMessageType = {
        role: "user",
        content: "Line 1\nLine 2\n  Indented",
      };

      const { container } = render(<ChatMessage message={messageWithWhitespace} />);

      const messageElement = container.querySelector("p");
      expect(messageElement).toHaveClass("whitespace-pre-wrap");
    });

    it("should apply correct styling for user messages", () => {
      const { container } = render(<ChatMessage message={userMessage} />);

      // Should have right-aligned flex container
      const messageContainer = container.firstChild;
      expect(messageContainer).toHaveClass("justify-end");

      // Should have primary background color
      const messageBox = container.querySelector("div.bg-primary");
      expect(messageBox).toBeInTheDocument();
    });
  });

  describe("Assistant Messages", () => {
    const assistantMessage: ChatMessageType = {
      role: "assistant",
      content: "# Hello!\n\nI can help you with many tasks.",
    };

    it("should render assistant message content", () => {
      render(<ChatMessage message={assistantMessage} />);

      // MarkdownRenderer should process the markdown
      // Check for the "Hello!" text (header will be rendered)
      expect(screen.getByText("Hello!")).toBeInTheDocument();
    });

    it("should display 'AI' avatar for assistant messages", () => {
      render(<ChatMessage message={assistantMessage} />);

      expect(screen.getByText("AI")).toBeInTheDocument();
    });

    it("should render markdown content", () => {
      const markdownMessage: ChatMessageType = {
        role: "assistant",
        content: "Here's some **bold** and *italic* text.",
      };

      render(<ChatMessage message={markdownMessage} />);

      // MarkdownRenderer component should handle this
      // Just verify the content is passed through
      expect(screen.getByText(/bold/)).toBeInTheDocument();
    });

    it("should apply correct styling for assistant messages", () => {
      const { container } = render(<ChatMessage message={assistantMessage} />);

      // Should NOT have justify-end (left-aligned)
      const messageContainer = container.firstChild;
      expect(messageContainer).not.toHaveClass("justify-end");

      // Should have flex gap for avatar spacing
      expect(messageContainer).toHaveClass("gap-4");
    });

    it("should use MarkdownRenderer component", () => {
      const { container } = render(<ChatMessage message={assistantMessage} />);

      // MarkdownRenderer should be present
      const markdownContainer = container.querySelector(".min-w-0.flex-1");
      expect(markdownContainer).toBeInTheDocument();
    });
  });

  describe("System Messages", () => {
    const systemMessage: ChatMessageType = {
      role: "system",
      content: "System notification",
    };

    it("should not render system messages", () => {
      const { container } = render(<ChatMessage message={systemMessage} />);

      expect(container.firstChild).toBeNull();
    });
  });

  describe("Animations", () => {
    it("should apply fade-in animation to user messages", () => {
      const userMessage: ChatMessageType = {
        role: "user",
        content: "Test",
      };

      const { container } = render(<ChatMessage message={userMessage} />);

      const messageContainer = container.firstChild;
      expect(messageContainer).toHaveClass("animate-in");
      expect(messageContainer).toHaveClass("fade-in-0");
      expect(messageContainer).toHaveClass("slide-in-from-bottom-2");
    });

    it("should apply fade-in animation to assistant messages", () => {
      const assistantMessage: ChatMessageType = {
        role: "assistant",
        content: "Test",
      };

      const { container } = render(<ChatMessage message={assistantMessage} />);

      const messageContainer = container.firstChild;
      expect(messageContainer).toHaveClass("animate-in");
      expect(messageContainer).toHaveClass("fade-in-0");
      expect(messageContainer).toHaveClass("slide-in-from-bottom-2");
    });
  });

  describe("Custom CSS Classes", () => {
    it("should apply custom className to user messages", () => {
      const userMessage: ChatMessageType = {
        role: "user",
        content: "Test",
      };

      const { container } = render(
        <ChatMessage message={userMessage} className="custom-class" />
      );

      const messageContainer = container.firstChild;
      expect(messageContainer).toHaveClass("custom-class");
    });

    it("should apply custom className to assistant messages", () => {
      const assistantMessage: ChatMessageType = {
        role: "assistant",
        content: "Test",
      };

      const { container } = render(
        <ChatMessage message={assistantMessage} className="custom-class" />
      );

      const messageContainer = container.firstChild;
      expect(messageContainer).toHaveClass("custom-class");
    });
  });

  describe("Responsive Styling", () => {
    it("should have responsive max-width for user messages", () => {
      const userMessage: ChatMessageType = {
        role: "user",
        content: "Test",
      };

      const { container } = render(<ChatMessage message={userMessage} />);

      const messageBox = container.querySelector(".max-w-\\[85\\%\\]");
      expect(messageBox).toBeInTheDocument();
      expect(messageBox).toHaveClass("md:max-w-[75%]");
    });
  });

  describe("Avatar Styling", () => {
    it("should render avatar with correct size", () => {
      const userMessage: ChatMessageType = {
        role: "user",
        content: "Test",
      };

      const { container } = render(<ChatMessage message={userMessage} />);

      const avatar = container.querySelector(".h-8.w-8");
      expect(avatar).toBeInTheDocument();
      expect(avatar).toHaveClass("shrink-0");
    });
  });

  describe("Content Handling", () => {
    it("should handle empty content", () => {
      const emptyMessage: ChatMessageType = {
        role: "user",
        content: "",
      };

      const { container } = render(<ChatMessage message={emptyMessage} />);

      // Should still render the message structure
      expect(container.firstChild).not.toBeNull();
    });

    it("should handle long content without breaking layout", () => {
      const longMessage: ChatMessageType = {
        role: "user",
        content: "A".repeat(500),
      };

      const { container } = render(<ChatMessage message={longMessage} />);

      // Should have max-width constraint
      const messageBox = container.querySelector(".max-w-\\[85\\%\\]");
      expect(messageBox).toBeInTheDocument();
    });

    it("should handle special characters", () => {
      const specialCharMessage: ChatMessageType = {
        role: "user",
        content: "<script>alert('test')</script>",
      };

      render(<ChatMessage message={specialCharMessage} />);

      // Should render as text, not execute
      expect(screen.getByText(/<script>alert\('test'\)<\/script>/)).toBeInTheDocument();
    });
  });
});
