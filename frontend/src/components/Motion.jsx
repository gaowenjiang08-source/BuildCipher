function cn(...values) {
  return values.filter(Boolean).join(" ");
}

export function MotionReveal({ as: Component = "div", children, className = "", delay = 0, variant = "up" }) {
  return (
    <Component
      className={cn("cg-motion-reveal", variant === "soft" ? "cg-motion-reveal--soft" : "", className)}
      style={{ "--cg-motion-delay": `${delay}ms` }}
    >
      {children}
    </Component>
  );
}

export function MotionCard({ as: Component = "div", children, className = "", delay = 0, selected = false }) {
  return (
    <Component
      className={cn("cg-motion-card cg-motion-reveal", selected ? "cg-motion-card--selected" : "", className)}
      style={{ "--cg-motion-delay": `${delay}ms` }}
    >
      {children}
    </Component>
  );
}

export function MotionStatus({ children, className = "", tone = "info" }) {
  return <span className={cn("cg-motion-status", `cg-motion-status--${tone}`, className)}>{children}</span>;
}
