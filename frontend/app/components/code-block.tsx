import { useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/cjs/styles/prism";
import { CheckIcon, CopyIcon } from "lucide-react";
import { Button } from "./ui/button";
import { cn } from "~/lib/utils";

interface CodeBlockProps {
  language?: string;
  children: string;
  className?: string;
}

export function CodeBlock({ language, children, className }: CodeBlockProps) {
  const [isCopied, setIsCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(children);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  return (
    <div className={cn("group relative my-4", className)}>
      {/* Header with language and copy button */}
      <div className="flex items-center justify-between rounded-t-lg bg-zinc-800 px-4 py-2 text-xs text-zinc-400">
        <span className="font-mono">{language || "text"}</span>
        <Button
          onClick={handleCopy}
          size="sm"
          variant="ghost"
          className="h-7 gap-1.5 px-2 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-100"
        >
          {isCopied ? (
            <>
              <CheckIcon className="h-3.5 w-3.5" />
              <span className="text-xs">Copied!</span>
            </>
          ) : (
            <>
              <CopyIcon className="h-3.5 w-3.5" />
              <span className="text-xs">Copy code</span>
            </>
          )}
        </Button>
      </div>

      {/* Code content */}
      <div className="overflow-x-auto rounded-b-lg">
        <SyntaxHighlighter
          language={language || "text"}
          style={vscDarkPlus}
          customStyle={{
            margin: 0,
            borderTopLeftRadius: 0,
            borderTopRightRadius: 0,
            fontSize: "0.875rem",
            lineHeight: "1.5",
          }}
          showLineNumbers={false}
          wrapLongLines={false}
        >
          {children}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}
