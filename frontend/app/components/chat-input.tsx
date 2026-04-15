/**
 * Chat Input Component
 *
 * A rich text input component for chat interfaces with auto-resize,
 * keyboard shortcuts, and loading states.
 *
 * @example
 * ```tsx
 * <ChatInput
 *   onSend={(message) => console.log(message)}
 *   isLoading={false}
 *   placeholder="Ask me anything..."
 * />
 * ```
 */

import { useState, useRef, useEffect } from "react";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { SendHorizontalIcon, LoaderIcon } from "lucide-react";
import { cn } from "~/lib/utils";

/**
 * Props for the ChatInput component
 */
interface ChatInputProps {
  /** Callback fired when user sends a message (Enter or button click) */
  onSend: (message: string) => void;

  /** Whether the input is disabled (e.g., not authenticated) */
  disabled?: boolean;

  /** Whether a request is in progress (shows loading spinner) */
  isLoading?: boolean;

  /** Placeholder text shown when input is empty */
  placeholder?: string;

  /** Additional CSS classes to apply to the container */
  className?: string;
}

/**
 * Chat input component with auto-resize and keyboard shortcuts
 *
 * Features:
 * - Auto-resizing textarea (up to 200px max height)
 * - Enter to send, Shift+Enter for new line
 * - Loading state with spinner
 * - Disabled state handling
 * - Trim whitespace on send
 *
 * @param props - ChatInputProps
 */
export function ChatInput({
  onSend,
  disabled = false,
  isLoading = false,
  placeholder = "Type your message...",
  className,
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (!value.trim() || disabled || isLoading) return;
    onSend(value.trim());
    setValue("");

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [value]);

  const canSend = value.trim().length > 0 && !disabled && !isLoading;

  return (
    <div
      className={cn(
        "bg-background focus-within:ring-ring relative flex items-end gap-3 rounded-3xl border px-4 py-3 shadow-sm transition-shadow focus-within:shadow-md focus-within:ring-1",
        disabled && "opacity-50",
        className
      )}
    >
      <Textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled || isLoading}
        className="placeholder:text-muted-foreground max-h-[200px] min-h-[24px] flex-1 resize-none border-0 bg-transparent p-0 text-sm shadow-none outline-none focus-visible:ring-0 focus-visible:ring-offset-0 focus-visible:outline-none disabled:cursor-not-allowed"
        rows={1}
      />
      <Button
        onClick={handleSend}
        disabled={!canSend}
        size="icon"
        className={cn(
          "h-8 w-8 shrink-0 rounded-lg transition-all",
          canSend
            ? "bg-primary text-primary-foreground hover:bg-primary/90"
            : "bg-muted text-muted-foreground"
        )}
        aria-label="Send message"
      >
        {isLoading ? (
          <LoaderIcon className="h-4 w-4 animate-spin" />
        ) : (
          <SendHorizontalIcon className="h-4 w-4" />
        )}
      </Button>
    </div>
  );
}
