import * as React from "react";
import { cn } from "@/lib/utils";

interface ListItemProps extends React.ComponentProps<"button"> {
  disabled?: boolean;
}

function ListItem({ className, disabled, children, ...props }: ListItemProps) {
  return (
    <button
      className={cn(
        "flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0",
        className,
      )}
      data-slot="list-item"
      disabled={disabled}
      type="button"
      {...props}
    >
      {children}
    </button>
  );
}

export { ListItem };
export type { ListItemProps };
