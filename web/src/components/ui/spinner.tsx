import * as React from "react";
import { cn } from "@/lib/utils";

interface SpinnerProps {
  className?: string;
  size?: number;
}

function Spinner({ className, size = 20 }: SpinnerProps) {
  return (
    <svg
      className={cn("animate-spin text-primary", className)}
      data-slot="spinner"
      fill="none"
      height={size}
      viewBox="0 0 24 24"
      width={size}
      xmlns="http://www.w3.org/2000/svg"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
        fill="currentColor"
      />
    </svg>
  );
}

export { Spinner };
