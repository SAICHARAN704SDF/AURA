import type { ButtonHTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

const buttonVariants = cva("inline-flex items-center justify-center gap-2", {
  variants: {
    variant: {
      default: "primary",
      outline: "border border-neutral-300 bg-white",
      ghost: "border-0 bg-transparent",
    },
  },
  defaultVariants: { variant: "default" },
});
export function Button({
  variant,
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants>) {
  return (
    <button
      {...props}
      className={twMerge(clsx(buttonVariants({ variant }), className))}
    />
  );
}
