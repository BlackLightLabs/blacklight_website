/**
 * Chat Message Component
 *
 * Renders a single chat message with appropriate styling for user vs assistant.
 * Assistant messages support markdown rendering with code highlighting.
 *
 * @example
 * ```tsx
 * <ChatMessage
 *   message={{ role: "user", content: "Hello!" }}
 * />
 * <ChatMessage
 *   message={{ role: "assistant", content: "# Hello\n\nHow can I help?" }}
 * />
 * ```
 */

import { Avatar, AvatarFallback } from "./ui/avatar";
import { MarkdownRenderer } from "./markdown-renderer";
import { cn } from "~/lib/utils";
import type { ChatMessage as ChatMessageType } from "~/lib/api";

/**
 * Props for the ChatMessage component
 */
interface ChatMessageProps {
  /** The message to display (includes role and content) */
  message: ChatMessageType;

  /** Additional CSS classes to apply to the container */
  className?: string;
}

/**
 * Renders a chat message with role-specific styling
 *
 * Message Types:
 * - User messages: Right-aligned, in a colored box, limited width
 * - Assistant messages: Left-aligned, full width, markdown support
 * - System messages: Currently returns null (not rendered)
 *
 * Features:
 * - Fade-in animations
 * - Avatar indicators
 * - Responsive max-width (85% mobile, 75% desktop)
 * - Markdown rendering for assistant messages
 * - Preserved whitespace for user messages
 *
 * @param props - ChatMessageProps
 */
export function ChatMessage({ message, className }: ChatMessageProps) {
  const isUser = message.role === "user";
  const isAssistant = message.role === "assistant";

  // User messages: Keep in a box with limited width
  if (isUser) {
    return (
      <div
        className={cn(
          "animate-in fade-in-0 slide-in-from-bottom-2 flex justify-end gap-3 duration-300",
          className
        )}
      >
        <div className="bg-primary text-primary-foreground max-w-[85%] rounded-lg px-4 py-3 shadow-sm md:max-w-[75%]">
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
        </div>

        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback className="bg-secondary text-secondary-foreground text-xs">
            You
          </AvatarFallback>
        </Avatar>
      </div>
    );
  }

  // AI messages: Full width with markdown rendering
  if (isAssistant) {
    return (
      <div
        className={cn(
          "animate-in fade-in-0 slide-in-from-bottom-2 flex gap-4 duration-300",
          className
        )}
      >
        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback className="bg-primary text-primary-foreground text-xs">AI</AvatarFallback>
        </Avatar>

        <div className="min-w-0 flex-1 pt-1">
          <MarkdownRenderer content={message.content} />
        </div>
      </div>
    );
  }

  return null;
}
