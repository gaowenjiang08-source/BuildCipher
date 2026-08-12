function BaseIcon({ children, className = "", size = 18, strokeWidth = 1.8, ...props }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={strokeWidth}
      className={className}
      width={size}
      height={size}
      aria-hidden="true"
      {...props}
    >
      {children}
    </svg>
  );
}

export function ArrowRightIcon(props) {
  return (
    <BaseIcon {...props}>
      <path d="M5 12h14" />
      <path d="m13 6 6 6-6 6" />
    </BaseIcon>
  );
}

export function BriefcaseIcon(props) {
  return (
    <BaseIcon {...props}>
      <path d="M8 7V5.5A1.5 1.5 0 0 1 9.5 4h5A1.5 1.5 0 0 1 16 5.5V7" />
      <rect x="4" y="7" width="16" height="12" rx="2.5" />
      <path d="M4 11.5h16" />
    </BaseIcon>
  );
}

export function CompassIcon(props) {
  return (
    <BaseIcon {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="m14.8 9.2-1.9 5-5 1.9 1.9-5 5-1.9Z" />
    </BaseIcon>
  );
}

export function CpuIcon(props) {
  return (
    <BaseIcon {...props}>
      <rect x="7" y="7" width="10" height="10" rx="2" />
      <path d="M9.5 9.5h5v5h-5z" />
      <path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3" />
    </BaseIcon>
  );
}

export function GridIcon(props) {
  return (
    <BaseIcon {...props}>
      <rect x="4" y="4" width="7" height="7" rx="1.5" />
      <rect x="13" y="4" width="7" height="7" rx="1.5" />
      <rect x="4" y="13" width="7" height="7" rx="1.5" />
      <rect x="13" y="13" width="7" height="7" rx="1.5" />
    </BaseIcon>
  );
}

export function LayersIcon(props) {
  return (
    <BaseIcon {...props}>
      <path d="m12 4 8 4-8 4-8-4 8-4Z" />
      <path d="m4 12 8 4 8-4" />
      <path d="m4 16 8 4 8-4" />
    </BaseIcon>
  );
}

export function PulseIcon(props) {
  return (
    <BaseIcon {...props}>
      <path d="M3 12h4l2.1-4.4L13 17l2.2-5h5.8" />
    </BaseIcon>
  );
}

export function SettingsIcon(props) {
  return (
    <BaseIcon {...props}>
      <circle cx="12" cy="12" r="3.2" />
      <path d="M19.4 15a1 1 0 0 0 .2 1.1l.1.1a1.9 1.9 0 1 1-2.7 2.7l-.1-.1a1 1 0 0 0-1.1-.2 1 1 0 0 0-.6.9V20a1.9 1.9 0 1 1-3.8 0v-.1a1 1 0 0 0-.6-.9 1 1 0 0 0-1.1.2l-.1.1a1.9 1.9 0 1 1-2.7-2.7l.1-.1a1 1 0 0 0 .2-1.1 1 1 0 0 0-.9-.6H4a1.9 1.9 0 1 1 0-3.8h.1a1 1 0 0 0 .9-.6 1 1 0 0 0-.2-1.1l-.1-.1a1.9 1.9 0 1 1 2.7-2.7l.1.1a1 1 0 0 0 1.1.2h.1a1 1 0 0 0 .6-.9V4a1.9 1.9 0 1 1 3.8 0v.1a1 1 0 0 0 .6.9h.1a1 1 0 0 0 1.1-.2l.1-.1a1.9 1.9 0 1 1 2.7 2.7l-.1.1a1 1 0 0 0-.2 1.1v.1a1 1 0 0 0 .9.6H20a1.9 1.9 0 1 1 0 3.8h-.1a1 1 0 0 0-.9.6Z" />
    </BaseIcon>
  );
}

export function ShieldIcon(props) {
  return (
    <BaseIcon {...props}>
      <path d="M12 3 5.5 5.6V11c0 4.2 2.7 8 6.5 10 3.8-2 6.5-5.8 6.5-10V5.6L12 3Z" />
      <path d="m9.5 12 1.7 1.8 3.3-3.8" />
    </BaseIcon>
  );
}

export function SparkIcon(props) {
  return (
    <BaseIcon {...props}>
      <path d="m12 3 1.7 4.8L18.5 9l-4.8 1.2L12 15l-1.7-4.8L5.5 9l4.8-1.2L12 3Z" />
      <path d="m18 15 1 2.8 2.8 1-2.8 1-1 2.8-1-2.8-2.8-1 2.8-1 1-2.8Z" />
    </BaseIcon>
  );
}

export function CheckCircleIcon(props) {
  return (
    <BaseIcon {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="m8.8 12 2.2 2.2 4.4-4.7" />
    </BaseIcon>
  );
}

export function AlertCircleIcon(props) {
  return (
    <BaseIcon {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 8v4.2" />
      <path d="M12 16h.01" />
    </BaseIcon>
  );
}

export function InfoCircleIcon(props) {
  return (
    <BaseIcon {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 10.2h.01" />
      <path d="M11.2 12.5H12v3" />
    </BaseIcon>
  );
}

export function HomeIcon(props) {
  return (
    <BaseIcon {...props}>
      <path d="M4 11.5 12 5l8 6.5" />
      <path d="M6.5 10.5V19h11v-8.5" />
      <path d="M10 19v-4.5h4V19" />
    </BaseIcon>
  );
}

export function FolderIcon(props) {
  return (
    <BaseIcon {...props}>
      <path d="M4 7.5A2.5 2.5 0 0 1 6.5 5h3.2l1.8 2H17.5A2.5 2.5 0 0 1 20 9.5v7A2.5 2.5 0 0 1 17.5 19h-11A2.5 2.5 0 0 1 4 16.5z" />
    </BaseIcon>
  );
}

export function ShareIcon(props) {
  return (
    <BaseIcon {...props}>
      <circle cx="17.5" cy="6.5" r="2" />
      <circle cx="6.5" cy="12" r="2" />
      <circle cx="17.5" cy="17.5" r="2" />
      <path d="m8.3 11 7.1-3.5" />
      <path d="m8.3 13 7.1 3.5" />
    </BaseIcon>
  );
}

export function BellIcon(props) {
  return (
    <BaseIcon {...props}>
      <path d="M6.5 16.5h11l-1-1.7V10a4.5 4.5 0 1 0-9 0v4.8z" />
      <path d="M10 18.5a2 2 0 0 0 4 0" />
    </BaseIcon>
  );
}

export function UserCircleIcon(props) {
  return (
    <BaseIcon {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <circle cx="12" cy="9.5" r="2.2" />
      <path d="M7.8 17c1.1-1.8 2.7-2.7 4.2-2.7s3.1.9 4.2 2.7" />
    </BaseIcon>
  );
}

export function ChevronDownIcon(props) {
  return (
    <BaseIcon {...props}>
      <path d="m6 9 6 6 6-6" />
    </BaseIcon>
  );
}

export function DatabaseIcon(props) {
  return (
    <BaseIcon {...props}>
      <ellipse cx="12" cy="6.5" rx="6.5" ry="2.5" />
      <path d="M5.5 6.5v5c0 1.4 2.9 2.5 6.5 2.5s6.5-1.1 6.5-2.5v-5" />
      <path d="M5.5 11.5v5c0 1.4 2.9 2.5 6.5 2.5s6.5-1.1 6.5-2.5v-5" />
    </BaseIcon>
  );
}

export function FlowIcon(props) {
  return (
    <BaseIcon {...props}>
      <rect x="4" y="5" width="6" height="4.5" rx="1.2" />
      <rect x="14" y="5" width="6" height="4.5" rx="1.2" />
      <rect x="9" y="14.5" width="6" height="4.5" rx="1.2" />
      <path d="M10 7.2h4" />
      <path d="M12 9.5v5" />
    </BaseIcon>
  );
}

export function AlertTriangleIcon(props) {
  return (
    <BaseIcon {...props}>
      <path d="m12 4 8 14H4l8-14Z" />
      <path d="M12 9v4.2" />
      <path d="M12 16h.01" />
    </BaseIcon>
  );
}

export function ClockIcon(props) {
  return (
    <BaseIcon {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 8v4.5l3 1.7" />
    </BaseIcon>
  );
}

export function CheckBadgeIcon(props) {
  return (
    <BaseIcon {...props}>
      <path d="M12 3.5 15 5l3.3-.2 1.2 3.1 2.3 2.4-1.6 2.8.2 3.3-3.1 1.2L15 20.5l-3-1.5-3 1.5-2.3-2.9-3.1-1.2.2-3.3-1.6-2.8 2.3-2.4L5.7 4.8 9 5z" />
      <path d="m9.2 12.1 1.9 1.9 3.8-4.1" />
    </BaseIcon>
  );
}

export function UploadIcon(props) {
  return (
    <BaseIcon {...props}>
      <path d="M12 15V6" />
      <path d="m8.5 9.5 3.5-3.5 3.5 3.5" />
      <path d="M5 17.5V19h14v-1.5" />
    </BaseIcon>
  );
}

export function LockIcon(props) {
  return (
    <BaseIcon {...props}>
      <rect x="5.5" y="10" width="13" height="9" rx="2" />
      <path d="M8.5 10V7.8A3.5 3.5 0 0 1 12 4.3a3.5 3.5 0 0 1 3.5 3.5V10" />
      <path d="M12 13.2v2.6" />
    </BaseIcon>
  );
}
