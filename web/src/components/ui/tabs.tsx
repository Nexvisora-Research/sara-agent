import * as React from "react";
import { cn } from "@/lib/utils";

interface TabsProps {
  value: string;
  onValueChange: (value: string) => void;
  className?: string;
  children: React.ReactNode;
}

function Tabs({ value, onValueChange, className, children }: TabsProps) {
  return (
    <div className={cn("w-full", className)} data-slot="tabs">
      {React.Children.map(children, (child) => {
        if (React.isValidElement(child)) {
          return React.cloneElement(child as React.ReactElement, {
            value,
            onValueChange,
          });
        }
        return child;
      })}
    </div>
  );
}

interface TabsListProps {
  className?: string;
  children: React.ReactNode;
  value?: string;
  onValueChange?: (value: string) => void;
}

function TabsList({
  className,
  children,
  value,
  onValueChange,
}: TabsListProps) {
  return (
    <div
      className={cn(
        "inline-flex h-10 items-center justify-center rounded-md bg-muted p-1 text-muted-foreground",
        className,
      )}
      data-slot="tabs-list"
    >
      {React.Children.map(children, (child) => {
        if (React.isValidElement(child)) {
          return React.cloneElement(child as React.ReactElement, {
            activeTab: value,
            onTabChange: onValueChange,
          });
        }
        return child;
      })}
    </div>
  );
}

interface TabsTriggerProps {
  value: string;
  className?: string;
  children: React.ReactNode;
  activeTab?: string;
  onTabChange?: (value: string) => void;
}

function TabsTrigger({
  value,
  className,
  children,
  activeTab,
  onTabChange,
}: TabsTriggerProps) {
  const isActive = activeTab === value;
  return (
    <button
      onClick={() => onTabChange?.(value)}
      className={cn(
        "inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-xs font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
        isActive
          ? "bg-background text-foreground shadow-sm"
          : "hover:text-foreground",
        className,
      )}
      data-slot="tabs-trigger"
      type="button"
    >
      {children}
    </button>
  );
}

export { Tabs, TabsList, TabsTrigger };
