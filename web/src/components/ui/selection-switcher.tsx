import * as React from "react";
import { cn } from "@/lib/utils";
import { ChevronDown } from "lucide-react";

interface SelectionSwitcherProps {
  className?: string;
}

function SelectionSwitcher({ className }: SelectionSwitcherProps) {
  return (
    <div
      className={cn(
        "flex items-center gap-2 px-3 py-2 text-xs font-medium uppercase tracking-wider",
        className,
      )}
      data-slot="selection-switcher"
    >
      <div className="flex cursor-pointer items-center gap-1.5 rounded-md px-2 py-1 hover:bg-accent/50">
        <span className="size-2 rounded-full bg-primary" />
        <span>sara-agent</span>
        <ChevronDown className="size-3 text-muted-foreground" />
      </div>
    </div>
  );
}

export { SelectionSwitcher };
export type { SelectionSwitcherProps };
