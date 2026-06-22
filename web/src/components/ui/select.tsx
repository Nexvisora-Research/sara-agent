import { Select as SelectPrimitive } from "radix-ui";
import * as React from "react";
import { cn } from "@/lib/utils";

function Select({
  className,
  children,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Root> & {
  className?: string;
}) {
  return (
    <SelectPrimitive.Root data-slot="select" {...props}>
      <SelectPrimitive.Trigger
        className={cn(
          "flex h-9 w-full items-center justify-between gap-2 whitespace-nowrap rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50 [&>span]:line-clamp-1",
          className,
        )}
      >
        <SelectPrimitive.Value />
        <svg
          className="size-4 shrink-0 opacity-50"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          strokeWidth={2}
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </SelectPrimitive.Trigger>
      <SelectPrimitive.Portal>
        <SelectPrimitive.Content className="relative z-[140] max-h-64 min-w-[8rem] overflow-hidden rounded-md border bg-popover text-popover-foreground shadow-md data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95">
          <SelectPrimitive.Viewport className="p-1">
            {children}
          </SelectPrimitive.Viewport>
        </SelectPrimitive.Content>
      </SelectPrimitive.Portal>
    </SelectPrimitive.Root>
  );
}

function SelectOption({
  className,
  children,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Item>) {
  return (
    <SelectPrimitive.Item
      className={cn(
        "relative flex w-full cursor-pointer items-center gap-2 rounded-sm py-1.5 pr-8 pl-2 text-xs outline-none select-none focus:bg-accent focus:text-accent-foreground data-disabled:pointer-events-none data-disabled:opacity-50",
        className,
      )}
      data-slot="select-option"
      {...props}
    >
      <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
    </SelectPrimitive.Item>
  );
}

export { Select, SelectOption };
