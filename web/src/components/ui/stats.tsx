import * as React from "react";
import { cn } from "@/lib/utils";

interface StatsItem {
  label: string;
  value: string | number;
}

interface StatsProps {
  items: StatsItem[];
  className?: string;
}

function Stats({ items, className }: StatsProps) {
  return (
    <div
      className={cn(
        "grid grid-cols-2 gap-6 sm:grid-cols-3 lg:grid-cols-4",
        className,
      )}
    >
      {items.map((item) => (
        <div key={item.label} className="space-y-1">
          <p className="text-2xl font-bold tracking-tight">{item.value}</p>
          <p className="text-xs text-muted-foreground">{item.label}</p>
        </div>
      ))}
    </div>
  );
}

export { Stats };
export type { StatsItem, StatsProps };
