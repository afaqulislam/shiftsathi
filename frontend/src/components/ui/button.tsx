import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full text-sm font-medium transition-all duration-500 ease-silk active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary:
          "bg-accent text-white shadow-glow hover:brightness-110 hover:shadow-[0_0_0_1px_var(--accent-soft),0_22px_70px_-18px_var(--accent-glow)]",
        secondary:
          "bg-white/[0.06] text-foreground border border-white/10 hover:bg-white/[0.1]",
        outline:
          "border border-white/12 bg-transparent text-foreground hover:bg-white/[0.05]",
        ghost: "text-muted hover:bg-white/[0.06] hover:text-foreground",
        danger:
          "bg-danger/15 text-danger border border-danger/25 hover:bg-danger/25",
      },
      size: {
        sm: "h-8 px-3.5 text-xs",
        md: "h-10 px-4",
        lg: "h-12 px-6 text-[0.95rem]",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
