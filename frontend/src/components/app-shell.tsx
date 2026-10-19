"use client";

import {
  Activity,
  AlertTriangle,
  BadgeCheck,
  ClipboardList,
  LayoutDashboard,
  Library,
  LogOut,
  Menu,
  Settings,
  Sparkles,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/lib/auth";
import { humanize } from "@/lib/format";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/assistant", label: "AI Assistant", icon: Sparkles },
  { href: "/knowledge", label: "Knowledge Base", icon: Library },
  { href: "/incidents", label: "Incidents", icon: AlertTriangle },
  { href: "/work-orders", label: "Work Orders", icon: ClipboardList },
  { href: "/verified", label: "Verified Knowledge", icon: BadgeCheck },
  { href: "/activity", label: "Activity", icon: Activity },
  { href: "/settings", label: "Settings", icon: Settings },
];

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <div className="relative flex size-9 items-center justify-center rounded-2xl bg-accent/90 shadow-glow">
        <span className="text-sm font-semibold text-white">S</span>
        <span className="absolute inset-0 rounded-2xl border border-accent-soft/60" />
      </div>
      <div className="leading-tight">
        <p className="text-sm font-medium tracking-tight">ShiftSathi</p>
        <p className="text-[11px] text-faint">Frontline operations</p>
      </div>
    </div>
  );
}

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav className="flex flex-col gap-1">
      {NAV.map((item) => {
        const active =
          pathname === item.href || pathname.startsWith(`${item.href}/`);
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            className={cn(
              "group relative flex items-center gap-3 rounded-2xl px-3.5 py-2.5 text-sm transition-all duration-500 ease-silk",
              active
                ? "bg-white/[0.07] text-foreground shadow-inner-hairline"
                : "text-muted hover:bg-white/[0.04] hover:text-foreground",
            )}
          >
            {active ? (
              <span className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-full bg-accent" />
            ) : null}
            <Icon
              className="size-[18px] shrink-0"
              strokeWidth={1.5}
              aria-hidden
            />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

function UserPanel() {
  const { me, logout } = useAuth();
  const router = useRouter();
  if (!me) return null;
  const initials = me.user.full_name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <div className="flex items-center gap-3 rounded-2xl border border-white/[0.07] bg-white/[0.02] p-2.5">
      <div className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-white/[0.07] text-xs font-medium">
        {initials}
      </div>
      <div className="min-w-0 flex-1 leading-tight">
        <p className="truncate text-sm font-medium">{me.user.full_name}</p>
        <p className="truncate text-[11px] text-faint">
          {humanize(me.role)} · {me.organization.name}
        </p>
      </div>
      <Button
        variant="ghost"
        size="icon"
        aria-label="Sign out"
        onClick={() => {
          logout();
          router.replace("/login");
        }}
      >
        <LogOut className="size-4" strokeWidth={1.5} />
      </Button>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { me, loading } = useAuth();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !me) router.replace("/login");
  }, [loading, me, router]);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  if (loading || !me) {
    return (
      <div className="mx-auto flex min-h-[100dvh] max-w-7xl gap-6 p-4 sm:p-6">
        <div className="hidden w-64 shrink-0 lg:block">
          <Skeleton className="h-full min-h-[80vh] rounded-4xl" />
        </div>
        <div className="flex-1 space-y-4">
          <Skeleton className="h-24 rounded-4xl" />
          <Skeleton className="h-64 rounded-4xl" />
          <Skeleton className="h-64 rounded-4xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto flex min-h-[100dvh] w-full max-w-[1600px] gap-6 p-3 sm:p-5">
      {/* Desktop sidebar */}
      <aside className="sticky top-5 hidden h-[calc(100dvh-2.5rem)] w-[260px] shrink-0 flex-col rounded-4xl border border-white/[0.07] bg-white/[0.02] p-3 shadow-ambient lg:flex">
        <div className="px-2 py-3">
          <Brand />
        </div>
        <div className="mt-2 flex-1 overflow-y-auto">
          <NavLinks />
        </div>
        <UserPanel />
      </aside>

      {/* Mobile top bar */}
      <div className="fixed inset-x-3 top-3 z-40 flex items-center justify-between rounded-3xl border border-white/10 bg-[#0b0b0f]/85 p-3 shadow-ambient glass lg:hidden">
        <Brand />
        <Button
          variant="ghost"
          size="icon"
          aria-label="Open menu"
          onClick={() => setMobileOpen(true)}
        >
          <Menu className="size-5" strokeWidth={1.5} />
        </Button>
      </div>

      {/* Mobile overlay */}
      {mobileOpen ? (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-2xl lg:hidden">
          <div className="flex h-full flex-col p-4">
            <div className="flex items-center justify-between">
              <Brand />
              <Button
                variant="ghost"
                size="icon"
                aria-label="Close menu"
                onClick={() => setMobileOpen(false)}
              >
                <X className="size-5" strokeWidth={1.5} />
              </Button>
            </div>
            <div className="mt-8 flex-1">
              <NavLinks onNavigate={() => setMobileOpen(false)} />
            </div>
            <UserPanel />
          </div>
        </div>
      ) : null}

      {/* Content */}
      <main className="min-w-0 flex-1 pb-10 pt-20 lg:pt-0">{children}</main>
    </div>
  );
}
