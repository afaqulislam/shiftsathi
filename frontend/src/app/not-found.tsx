import { Compass } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main className="relative flex min-h-[100dvh] flex-col items-center justify-center gap-6 px-6 text-center">
      <div className="flex size-14 items-center justify-center rounded-3xl border border-white/10 bg-white/[0.04]">
        <Compass className="size-6 text-accent" strokeWidth={1.5} />
      </div>
      <div className="space-y-2">
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-faint">
          404
        </p>
        <h1 className="text-xl font-medium tracking-tight">Page not found</h1>
        <p className="mx-auto max-w-sm text-sm text-muted">
          The page you are looking for doesn&apos;t exist or has been moved.
        </p>
      </div>
      <div className="flex items-center gap-3">
        <Button asChild>
          <Link href="/dashboard">Back to dashboard</Link>
        </Button>
        <Button variant="ghost" asChild>
          <Link href="/assistant">Ask the assistant</Link>
        </Button>
      </div>
    </main>
  );
}
