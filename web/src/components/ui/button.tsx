import { cva, type VariantProps } from "class-variance-authority";
import { Slot } from "radix-ui";
import * as React from "react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex shrink-0 cursor-pointer items-center justify-center gap-1.5 rounded-[2.5px] text-xs leading-4 font-medium whitespace-nowrap shadow-none transition-all duration-100 outline-none focus-visible:border-ring focus-visible:ring-[0.1875rem] focus-visible:ring-ring/50 disabled:pointer-events-none disabled:cursor-default disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-3.5",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive:
          "bg-destructive text-white hover:bg-destructive/90 focus-visible:ring-destructive/20",
        outline:
          "bg-transparent shadow-[inset_0_0_0_1px_var(--border)] hover:bg-accent hover:text-accent-foreground",
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 decoration-current/20 hover:underline [&_svg]:no-underline",
        text: "text-muted-foreground underline-offset-4 hover:text-foreground hover:underline [&_svg]:no-underline",
        textStrong:
          "font-semibold text-muted-foreground underline underline-offset-4 hover:text-foreground [&_svg]:no-underline",
      },
      size: {
        default: "px-3 py-1.5 has-[>svg]:px-2.5",
        xs: "gap-1 px-2 py-0.5 text-[0.6875rem] leading-4 has-[>svg]:px-1.5 [&_svg:not([class*='size-'])]:size-3",
        sm: "px-2.5 py-1 has-[>svg]:px-2",
        lg: "px-5 py-2 text-sm leading-5 has-[>svg]:px-4",
        inline: "h-auto gap-1 p-0 has-[>svg]:px-0",
        micro:
          "h-auto gap-0.5 px-1 py-0 text-xs leading-4 font-normal has-[>svg]:px-0.5 [&_svg:not([class*='size-'])]:size-3",
        icon: "size-9 rounded-[4px]",
        "icon-xs": "size-6 rounded-[4px] [&_svg:not([class*='size-'])]:size-3",
        "icon-sm": "size-8 rounded-[4px]",
        "icon-lg": "size-10 rounded-[4px]",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ComponentProps<"button">,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ asChild = false, className, variant, size, ...props }, ref) => {
    const Comp = asChild ? Slot.Root : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size }), className)}
        ref={ref}
        data-slot="button"
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
