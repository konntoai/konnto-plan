import { Toaster as Sonner, toast } from "sonner"
import { useTheme } from "@/context/ThemeContext"

const Toaster = ({
  ...props
}) => {
  const { theme } = useTheme()

  return (
    <Sonner
      theme={theme}
      className="toaster group"
      visibleToasts={3}
      toastOptions={{
        classNames: {
          toast:
            "group toast group-[.toaster]:glass-strong group-[.toaster]:text-foreground group-[.toaster]:rounded-2xl group-[.toaster]:shadow-[0_20px_50px_-20px_hsl(var(--glass-shadow))] group-[.toaster]:font-sans",
          title: "group-[.toast]:font-semibold",
          description: "group-[.toast]:text-muted-foreground",
          actionButton:
            "group-[.toast]:bg-primary group-[.toast]:text-primary-foreground",
          cancelButton:
            "group-[.toast]:bg-muted group-[.toast]:text-muted-foreground",
          closeButton: "group-[.toast]:bg-card group-[.toast]:border-border group-[.toast]:text-foreground",
          success: "group-[.toaster]:!border-status-done/30 [&_[data-icon]]:text-status-done",
          error: "group-[.toaster]:!border-status-overdue/30 [&_[data-icon]]:text-status-overdue",
          warning: "group-[.toaster]:!border-status-due/30 [&_[data-icon]]:text-status-due",
          info: "group-[.toaster]:!border-primary/30 [&_[data-icon]]:text-primary",
        },
      }}
      {...props} />
  );
}

export { Toaster, toast }
