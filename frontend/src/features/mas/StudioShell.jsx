export default function StudioShell({ header, sidebar, notices, children }) {
  return (
    <div className="min-h-screen px-4 pb-12 pt-4 md:px-6 lg:px-8">
      <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute inset-0 bg-[linear-gradient(180deg,#f6f9ff_0%,#eef4fb_42%,#e4edf8_100%)]" />
        <div className="absolute inset-0 opacity-[0.2]" style={{ backgroundImage: "linear-gradient(rgba(148,163,184,0.14) 1px, transparent 1px), linear-gradient(90deg, rgba(148,163,184,0.14) 1px, transparent 1px)", backgroundSize: "72px 72px" }} />
        <div className="absolute left-[-10rem] top-[-8rem] h-[24rem] w-[24rem] rounded-full bg-[radial-gradient(circle,rgba(32,111,247,0.08)_0%,rgba(32,111,247,0)_70%)]" />
        <div className="absolute right-[-8rem] top-[3rem] h-[22rem] w-[22rem] rounded-full bg-[radial-gradient(circle,rgba(15,118,110,0.08)_0%,rgba(15,118,110,0)_70%)]" />
        <div className="absolute bottom-[-10rem] left-1/3 h-[22rem] w-[22rem] rounded-full bg-[radial-gradient(circle,rgba(99,102,241,0.08)_0%,rgba(99,102,241,0)_70%)]" />
        <div className="absolute left-[16%] top-[24%] h-[14rem] w-[14rem] rounded-full bg-[radial-gradient(circle,rgba(14,165,233,0.05)_0%,rgba(14,165,233,0)_72%)]" />
      </div>

      <div className="mx-auto max-w-[1680px]">
        <div className="relative z-40 lg:sticky lg:top-4">{header}</div>

        <div className="mt-6 grid gap-5 lg:grid-cols-[292px_minmax(0,1fr)] xl:gap-6">
          <div className="min-w-0 lg:sticky lg:top-[112px] lg:self-start">
            <div className="min-w-0 rounded-[28px] border border-white/60 bg-[linear-gradient(180deg,rgba(255,255,255,0.78)_0%,rgba(248,251,255,0.92)_100%)] p-1 shadow-[var(--cg-shadow-soft)] backdrop-blur-xl">
              {sidebar}
            </div>
          </div>

          <main className="min-w-0 space-y-5">
            {notices}
            <div className="relative">
              <div className="pointer-events-none absolute left-0 top-0 hidden h-full w-px bg-[linear-gradient(180deg,rgba(37,99,235,0.18),transparent_78%)] xl:block" />
              <div className="space-y-5 xl:pl-5">{children}</div>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
