"use client";

import { RefreshCw, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useEffect } from "react";

import { Button } from "@/components/ui/button";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="relative flex min-h-[100dvh] flex-col items-center justify-center gap-6 px-6 text-center">
      <div className="flex size-14 items-center justify-center rounded-3xl border border-danger/25 bg-danger/[0.07]">
        <TriangleAlert className="size-6 text-danger" strokeWidth={1.5} />
      </div>
      <div className="space-y-2">
        <h1 className="text-xl font-medium tracking-tight">
          Something went wrong
        </h1>
        <p className="mx-auto max-w-sm text-sm text-muted">
          An unexpected error occurred while rendering this page. You can retry,
          or head back to the dashboard.
        </p>
      </div>
      <div className="flex items-center gap-3">
        <Button onClick={reset}>
          <RefreshCw className="size-4" strokeWidth={1.5} />
          Try again
        </Button>
        <Button variant="ghost" asChild>
          <Link href="/dashboard">Back to dashboard</Link>
        </Button>
      </div>
    </main>
  );
}
