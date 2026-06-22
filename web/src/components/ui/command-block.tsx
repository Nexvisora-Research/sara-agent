import { Check, Copy } from "lucide-react";
import * as React from "react";
import { cn } from "@/lib/utils";

interface CommandBlockProps {
  label?: string;
  code: string;
  className?: string;
}

function CommandBlock({ label, code, className }: CommandBlockProps) {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={cn("space-y-2", className)}>
      {label && <p className="text-xs text-muted-foreground">{label}</p>}
      <div className="group relative">
        <pre className="overflow-x-auto rounded-lg border bg-muted p-3 text-xs font-mono">
          <code>{code}</code>
        </pre>
        <button
          onClick={handleCopy}
          className="absolute top-2 right-2 rounded-md p-1.5 opacity-0 transition-opacity group-hover:opacity-100 hover:bg-accent"
          type="button"
          aria-label={copied ? "Copied" : "Copy"}
        >
          {copied ? (
            <Check className="size-3.5 text-green-500" />
          ) : (
            <Copy className="size-3.5 text-muted-foreground" />
          )}
        </button>
      </div>
    </div>
  );
}

interface CopyButtonProps {
  text: string;
  label: string;
  copiedLabel: string;
  className?: string;
}

function CopyButton({ text, label, copiedLabel, className }: CopyButtonProps) {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors hover:bg-accent hover:text-accent-foreground",
        className,
      )}
      type="button"
    >
      {copied ? (
        <Check className="size-3.5 text-green-500" />
      ) : (
        <Copy className="size-3.5" />
      )}
      {copied ? copiedLabel : label}
    </button>
  );
}

export { CommandBlock, CopyButton };
export type { CommandBlockProps, CopyButtonProps };
