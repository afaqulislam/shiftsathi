import { BadgeCheck, ClipboardList, Sparkles } from "lucide-react";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="mx-auto grid min-h-[100dvh] w-full max-w-6xl grid-cols-1 items-center gap-12 px-4 py-12 lg:grid-cols-2 lg:px-8">
      <section className="hidden flex-col justify-center lg:flex">
        <span className="mb-6 inline-flex w-max rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-[10px] font-medium uppercase tracking-[0.22em] text-muted">
          Frontline operations
        </span>
        <h1 className="text-balance text-5xl font-medium leading-[1.05] tracking-tight">
          The assistant your
          <br />
          <span className="text-accent">shift floor</span> deserves.
        </h1>
        <p className="mt-6 max-w-md text-sm leading-relaxed text-muted">
          Grounded answers from your own manuals, verified resolutions that
          compound, and incident-to-work-order flow — all in one calm, auditable
          workspace.
        </p>
        <ul className="mt-10 space-y-4">
          {[
            { icon: Sparkles, text: "Answers cited to your documents — or an honest abstain." },
            { icon: ClipboardList, text: "Report incidents, assign work orders, track progress." },
            { icon: BadgeCheck, text: "Human-verified resolutions become searchable knowledge." },
          ].map((item) => (
            <li key={item.text} className="flex items-center gap-3 text-sm text-muted">
              <span className="flex size-8 items-center justify-center rounded-xl border border-white/10 bg-white/[0.04]">
                <item.icon className="size-4 text-accent" strokeWidth={1.5} />
              </span>
              {item.text}
            </li>
          ))}
        </ul>
      </section>
      <section className="flex w-full justify-center">{children}</section>
    </div>
  );
}
