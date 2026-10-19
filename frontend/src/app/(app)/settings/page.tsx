"use client";

import { CircleDot, KeyRound, Plus, ShieldCheck, UserPlus, Users } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate, humanize } from "@/lib/format";
import type { Member, Role } from "@/lib/types";
import { useAsyncData } from "@/lib/use-async";

const ROLES: Role[] = ["admin", "supervisor", "worker"];

const ROLE_TONE: Record<Role, "accent" | "info" | "neutral"> = {
  admin: "accent",
  supervisor: "info",
  worker: "neutral",
};

export default function SettingsPage() {
  const { me } = useAuth();
  const [inviting, setInviting] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);

  const { data: members, loading, reload } = useAsyncData<Member[]>(
    () => api.members(),
    [],
  );
  const { data: health } = useAsyncData(
    () => api.health().catch(() => null),
    [],
  );

  const isAdmin = me?.role === "admin";

  async function changeRole(userId: string, role: Role) {
    try {
      await api.changeRole(userId, role);
      toast.success("Role updated");
      void reload();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not update role.");
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Settings"
        title="Workspace & team"
        description="Manage your organization, members and their access levels."
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Organization</CardTitle>
            <CardDescription>Your current workspace.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Field label="Name" value={me?.organization.name ?? "—"} />
            <Field label="Slug" value={me?.organization.slug ?? "—"} mono />
            <Field
              label="Created"
              value={formatDate(me?.organization.created_at)}
            />
            <Field label="Your role" value={humanize(me?.role ?? "")} />
          </CardContent>
        </Card>

        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Account</CardTitle>
            <CardDescription>Signed-in operator.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Field label="Name" value={me?.user.full_name ?? "—"} />
            <Field label="Email" value={me?.user.email ?? "—"} />
            <Field
              label="Member since"
              value={formatDate(me?.user.created_at)}
            />
            <Button
              variant="outline"
              size="sm"
              className="w-full"
              onClick={() => setChangingPassword(true)}
            >
              <KeyRound className="size-4" strokeWidth={1.5} />
              Change password
            </Button>
          </CardContent>
        </Card>

        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>System</CardTitle>
            <CardDescription>Backend connectivity.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-2">
              <CircleDot
                className={
                  health
                    ? "size-3.5 text-success"
                    : "size-3.5 text-faint"
                }
                strokeWidth={2}
              />
              <span className="text-sm">
                {health ? "API reachable" : "API unreachable"}
              </span>
            </div>
            <Field
              label="Environment"
              value={health?.environment ?? "—"}
              mono
            />
            <Field
              label="Base URL"
              value={
                process.env.NEXT_PUBLIC_API_BASE_URL ??
                "http://localhost:8000/api/v1"
              }
              mono
            />
          </CardContent>
        </Card>
      </div>

      <Card className="mt-6">
        <CardContent className="p-6">
          <div className="mb-5 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Users className="size-4 text-faint" strokeWidth={1.5} />
              <CardTitle>Team members</CardTitle>
            </div>
            {isAdmin ? (
              <Button size="sm" onClick={() => setInviting(true)}>
                <UserPlus className="size-4" strokeWidth={1.5} />
                Invite member
              </Button>
            ) : null}
          </div>

          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-14 rounded-2xl" />
              ))}
            </div>
          ) : !members || members.length === 0 ? (
            <EmptyState icon={Users} title="No members yet" />
          ) : (
            <ul className="divide-y divide-white/[0.06]">
              {members.map((member) => (
                <li
                  key={member.user.id}
                  className="flex flex-wrap items-center justify-between gap-3 py-3.5"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex size-9 items-center justify-center rounded-xl bg-white/[0.07] text-xs font-medium">
                      {member.user.full_name
                        .split(" ")
                        .map((p) => p[0])
                        .slice(0, 2)
                        .join("")
                        .toUpperCase()}
                    </div>
                    <div className="leading-tight">
                      <p className="text-sm font-medium">
                        {member.user.full_name}
                        {member.user.id === me?.user.id ? (
                          <span className="ml-2 text-[11px] text-faint">you</span>
                        ) : null}
                      </p>
                      <p className="text-xs text-faint">{member.user.email}</p>
                    </div>
                  </div>
                  {isAdmin && member.user.id !== me?.user.id ? (
                    <Select
                      value={member.role}
                      onValueChange={(v) => void changeRole(member.user.id, v as Role)}
                    >
                      <SelectTrigger className="w-40">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {ROLES.map((r) => (
                          <SelectItem key={r} value={r}>
                            {humanize(r)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    <Badge tone={ROLE_TONE[member.role]}>
                      <ShieldCheck className="size-3" strokeWidth={2} />
                      {humanize(member.role)}
                    </Badge>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <InviteDialog
        open={inviting}
        onOpenChange={setInviting}
        onInvited={() => void reload()}
      />

      <ChangePasswordDialog
        open={changingPassword}
        onOpenChange={setChangingPassword}
      />
    </div>
  );
}

function Field({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-xs uppercase tracking-[0.14em] text-faint">
        {label}
      </span>
      <span
        className={`truncate text-sm text-foreground ${mono ? "font-mono text-xs" : ""}`}
      >
        {value}
      </span>
    </div>
  );
}

function InviteDialog({
  open,
  onOpenChange,
  onInvited,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onInvited: () => void;
}) {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("worker");
  const [busy, setBusy] = useState(false);

  function reset() {
    setFullName("");
    setEmail("");
    setPassword("");
    setRole("worker");
  }

  async function submit() {
    if (fullName.trim().length < 2 || !email.trim()) {
      toast.error("Name and email are required.");
      return;
    }
    if (password.length < 8) {
      toast.error("Password must be at least 8 characters.");
      return;
    }
    setBusy(true);
    try {
      await api.inviteMember({
        full_name: fullName.trim(),
        email: email.trim(),
        password,
        role,
      });
      toast.success("Member added");
      reset();
      onOpenChange(false);
      onInvited();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not add member.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Invite a member</DialogTitle>
          <DialogDescription>
            Create credentials for a teammate and choose their role.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="inv-name">Full name</Label>
            <Input
              id="inv-name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Bilal Ahmed"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="inv-email">Email</Label>
            <Input
              id="inv-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="teammate@factory.pk"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="inv-pass">Temporary password</Label>
              <Input
                id="inv-pass"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Min 8 characters"
              />
            </div>
            <div className="space-y-2">
              <Label>Role</Label>
              <Select value={role} onValueChange={(v) => setRole(v as Role)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ROLES.map((r) => (
                    <SelectItem key={r} value={r}>
                      {humanize(r)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <Button variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button onClick={() => void submit()} disabled={busy}>
              {busy ? "Adding…" : (
                <>
                  <Plus className="size-4" strokeWidth={1.5} />
                  Add member
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function ChangePasswordDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);

  function reset() {
    setCurrent("");
    setNext("");
    setConfirm("");
  }

  async function submit() {
    if (next.length < 8) {
      toast.error("New password must be at least 8 characters.");
      return;
    }
    if (!/[A-Za-z]/.test(next) || !/\d/.test(next)) {
      toast.error("New password must include a letter and a number.");
      return;
    }
    if (next !== confirm) {
      toast.error("New passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      await api.changePassword({
        current_password: current,
        new_password: next,
      });
      toast.success("Password updated");
      reset();
      onOpenChange(false);
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.message : "Could not update password.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) reset();
        onOpenChange(o);
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Change password</DialogTitle>
          <DialogDescription>
            Enter your current password and choose a new one.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="pw-current">Current password</Label>
            <Input
              id="pw-current"
              type="password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              autoComplete="current-password"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="pw-new">New password</Label>
            <Input
              id="pw-new"
              type="password"
              value={next}
              onChange={(e) => setNext(e.target.value)}
              placeholder="Min 8 characters, with a number"
              autoComplete="new-password"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="pw-confirm">Confirm new password</Label>
            <Input
              id="pw-confirm"
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              autoComplete="new-password"
            />
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <Button variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button onClick={() => void submit()} disabled={busy}>
              {busy ? "Updating…" : (
                <>
                  <KeyRound className="size-4" strokeWidth={1.5} />
                  Update password
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
