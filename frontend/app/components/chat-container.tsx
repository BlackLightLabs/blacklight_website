import { useEffect, useRef } from "react";
import { ScrollArea } from "./ui/scroll-area";
import { Skeleton } from "./ui/skeleton";
import { Avatar, AvatarFallback } from "./ui/avatar";
import { ChatMessage } from "./chat-message";
import { ChatInput } from "./chat-input";
import { cn } from "~/lib/utils";
import type { ChatMessage as ChatMessageType } from "~/lib/api";

interface ChatContainerProps {
  messages: ChatMessageType[];
  onSendMessage: (message: string) => void;
  isLoading?: boolean;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
  emptyState?: React.ReactNode;
}

export function ChatContainer({
  messages,
  onSendMessage,
  isLoading = false,
  disabled = false,
  placeholder = "Type your message...",
  className,
  emptyState,
}: ChatContainerProps) {
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const hasMessages = messages.length > 0;

  // ChatGPT-style: Center input when no messages
  if (!hasMessages && !isLoading) {
    return (
      <div className={cn("flex h-full flex-col items-center justify-center p-4", className)}>
        <div className="w-full max-w-3xl">
          <ChatInput
            onSend={onSendMessage}
            disabled={disabled}
            isLoading={isLoading}
            placeholder={placeholder}
          />
        </div>
      </div>
    );
  }

  return (
    <div className={cn("flex h-full flex-col", className)}>
      {/* Messages Area */}
      <div className="flex-1 overflow-hidden">
        <ScrollArea className="h-full" ref={scrollAreaRef}>
          <div className="mx-auto max-w-3xl space-y-4 px-4 py-6">
            {hasMessages &&
              messages.map((message, index) => <ChatMessage key={index} message={message} />)}

            {/* Loading Skeleton */}
            {isLoading && (
              <div className="animate-in fade-in-0 slide-in-from-bottom-2 flex justify-start gap-3 duration-300">
                <Avatar className="h-8 w-8 shrink-0">
                  <AvatarFallback className="bg-primary text-primary-foreground text-xs">
                    AI
                  </AvatarFallback>
                </Avatar>
                <div className="space-y-2">
                  <Skeleton className="h-4 w-[250px]" />
                  <Skeleton className="h-4 w-[200px]" />
                </div>
              </div>
            )}

            {/* Scroll anchor */}
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>
      </div>

      {/* Input Area - Fixed at bottom */}
      <div className="bg-background">
        <div className="mx-auto max-w-3xl px-4 py-6">
          <ChatInput
            onSend={onSendMessage}
            disabled={disabled}
            isLoading={isLoading}
            placeholder={placeholder}
          />
        </div>
      </div>
    </div>
  );
}
