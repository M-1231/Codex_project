import { ButtonHTMLAttributes, forwardRef } from "react";
export const Button = forwardRef<HTMLButtonElement, ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "default" | "outline" }>(({ className = "", variant = "default", ...props }, ref) => <button ref={ref} className={`inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium transition disabled:opacity-50 ${variant === "default" ? "bg-accent text-white hover:bg-indigo-700" : "border bg-white hover:bg-slate-50"} ${className}`} {...props} />);
Button.displayName = "Button";
