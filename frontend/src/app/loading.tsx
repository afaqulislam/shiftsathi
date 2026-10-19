export default function Loading() {
  return (
    <div className="flex min-h-[100dvh] items-center justify-center">
      <div className="flex items-center gap-2.5 text-xs text-faint">
        <span className="relative flex size-2">
          <span className="absolute inline-flex size-full animate-pulse-ring rounded-full bg-accent/60" />
          <span className="relative inline-flex size-2 rounded-full bg-accent" />
        </span>
        Loading…
      </div>
    </div>
  );
}
