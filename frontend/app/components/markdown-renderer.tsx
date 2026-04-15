import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { CodeBlock } from "./code-block";
import { cn } from "~/lib/utils";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  return (
    <div className={cn("prose prose-sm dark:prose-invert max-w-none", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Code blocks
          code({ node, inline, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || "");
            const language = match ? match[1] : undefined;
            const codeContent = String(children).replace(/\n$/, "");

            return !inline && language ? (
              <CodeBlock language={language}>{codeContent}</CodeBlock>
            ) : (
              <code
                className={cn(
                  "rounded bg-zinc-100 px-1.5 py-0.5 font-mono text-sm dark:bg-zinc-800",
                  className
                )}
                {...props}
              >
                {children}
              </code>
            );
          },

          // Paragraphs
          p({ children }) {
            return <p className="mb-4 leading-7 last:mb-0">{children}</p>;
          },

          // Headings
          h1({ children }) {
            return <h1 className="mt-6 mb-4 text-2xl font-semibold first:mt-0">{children}</h1>;
          },
          h2({ children }) {
            return <h2 className="mt-6 mb-3 text-xl font-semibold first:mt-0">{children}</h2>;
          },
          h3({ children }) {
            return <h3 className="mt-4 mb-3 text-lg font-semibold first:mt-0">{children}</h3>;
          },

          // Lists
          ul({ children }) {
            return <ul className="mb-4 ml-6 list-disc space-y-2 [&>li]:leading-7">{children}</ul>;
          },
          ol({ children }) {
            return (
              <ol className="mb-4 ml-6 list-decimal space-y-2 [&>li]:leading-7">{children}</ol>
            );
          },

          // Task lists
          li({ children, className }) {
            const isTaskList = className?.includes("task-list-item");
            return <li className={cn(isTaskList && "list-none", className)}>{children}</li>;
          },

          // Blockquotes
          blockquote({ children }) {
            return (
              <blockquote className="mb-4 border-l-4 border-zinc-300 pl-4 text-zinc-600 italic dark:border-zinc-700 dark:text-zinc-400">
                {children}
              </blockquote>
            );
          },

          // Tables
          table({ children }) {
            return (
              <div className="mb-4 overflow-x-auto">
                <table className="min-w-full divide-y divide-zinc-300 dark:divide-zinc-700">
                  {children}
                </table>
              </div>
            );
          },
          thead({ children }) {
            return <thead className="bg-zinc-50 dark:bg-zinc-900">{children}</thead>;
          },
          th({ children }) {
            return <th className="px-4 py-2 text-left text-sm font-semibold">{children}</th>;
          },
          td({ children }) {
            return (
              <td className="border-t border-zinc-200 px-4 py-2 text-sm dark:border-zinc-800">
                {children}
              </td>
            );
          },

          // Links
          a({ href, children }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:text-primary/80 underline underline-offset-2"
              >
                {children}
              </a>
            );
          },

          // Horizontal rule
          hr() {
            return <hr className="my-6 border-zinc-200 dark:border-zinc-800" />;
          },

          // Strong/Bold
          strong({ children }) {
            return <strong className="font-semibold">{children}</strong>;
          },

          // Emphasis/Italic
          em({ children }) {
            return <em className="italic">{children}</em>;
          },

          // Strikethrough (from GFM)
          del({ children }) {
            return <del className="line-through">{children}</del>;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
