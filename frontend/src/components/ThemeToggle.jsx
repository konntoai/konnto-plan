import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/context/ThemeContext";
import { cn } from "@/lib/utils";

export const ThemeToggle = ({ className = "", testid = "theme-toggle" }) => {
  const { theme, toggle } = useTheme();
  const dark = theme === "dark";
  return (
    <button
      type="button"
      onClick={toggle}
      data-testid={testid}
      aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}
      title={dark ? "Light theme" : "Dark theme"}
      className={cn(
        "relative h-10 w-10 grid place-items-center rounded-full glass text-foreground hover:text-primary btn-lift",
        "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        className
      )}
    >
      <Sun className={cn("h-[18px] w-[18px] absolute transition-[transform,opacity] duration-200", dark ? "opacity-0 rotate-90 scale-50" : "opacity-100 rotate-0 scale-100")} />
      <Moon className={cn("h-[18px] w-[18px] absolute transition-[transform,opacity] duration-200", dark ? "opacity-100 rotate-0 scale-100" : "opacity-0 -rotate-90 scale-50")} />
    </button>
  );
};

export default ThemeToggle;
