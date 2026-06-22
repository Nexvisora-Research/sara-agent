import * as React from "react";
import { cn } from "@/lib/utils";

interface SegmentedOption<T extends string> {
  value: T;
  label: string;
}

interface SegmentedProps<T extends string> {
  value: T;
  onChange: (value: T) => void;
  options: SegmentedOption<T>[];
  className?: string;
}

function Segmented<T extends string>({
  value,
  onChange,
  options,
  className,
}: SegmentedProps<T>) {
  return (
    <div className={cn("inline-flex rounded-lg bg-muted p-1", className)}>
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={cn(
            "rounded-md px-3 py-1.5 text-xs font-medium transition-all",
            value === opt.value
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground",
          )}
          type="button"
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

interface FilterGroupProps {
  label: string;
  children: React.ReactNode;
  className?: string;
}

function FilterGroup({ label, children, className }: FilterGroupProps) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <span className="text-xs text-muted-foreground">{label}</span>
      {children}
    </div>
  );
}

export { Segmented, FilterGroup };
export type { SegmentedOption, SegmentedProps, FilterGroupProps };
