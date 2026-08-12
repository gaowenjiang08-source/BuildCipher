import { AlertCircleIcon, CheckCircleIcon, InfoCircleIcon } from "../../components/Icons";

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

const TONE_STYLES = {
  success: {
    shell: "border-[color:var(--cg-success-border)] bg-[color:var(--cg-success-fog)] text-[color:var(--cg-success-text)]",
    icon: CheckCircleIcon,
  },
  error: {
    shell: "border-[color:var(--cg-danger-border)] bg-[color:var(--cg-danger-fog)] text-[color:var(--cg-danger-text)]",
    icon: AlertCircleIcon,
  },
  info: {
    shell: "border-[color:var(--cg-accent-border)] bg-[color:var(--cg-accent-fog)] text-[color:var(--cg-accent-strong)]",
    icon: InfoCircleIcon,
  },
};

export default function WorkspaceStatusBanner({ message, tone = "info" }) {
  if (!message) return null;

  const currentTone = TONE_STYLES[tone] || TONE_STYLES.info;
  const Icon = currentTone.icon;
  const displayMessage = message === "Failed to fetch" ? "后端服务未连接，请启动 API 后重试。" : message;

  return (
    <section
      className={cn(
        "flex items-start gap-3 rounded-[22px] border px-4 py-3.5 text-sm font-medium shadow-[var(--cg-shadow-soft)]",
        currentTone.shell
      )}
    >
      <span className="mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-current/15 bg-white/55">
        <Icon size={16} />
      </span>
      <p className="min-w-0 flex-1 leading-7">{displayMessage}</p>
    </section>
  );
}
