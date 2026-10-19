"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const schema = z.object({
  email: z.string().email("Enter a valid email address."),
  password: z.string().min(1, "Password is required."),
});

type FormValues = z.infer<typeof schema>;

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
  });

  async function onSubmit(values: FormValues) {
    try {
      await login(values.email, values.password);
      toast.success("Welcome back");
      router.replace("/dashboard");
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.message : "Unable to sign in right now.",
      );
    }
  }

  return (
    <Card className="w-full max-w-md">
      <CardContent className="p-7">
        <CardHeader className="px-0 pt-0">
          <CardTitle className="text-2xl">Sign in</CardTitle>
          <CardDescription>
            Enter your workspace credentials to continue.
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="you@factory.pk"
              {...register("email")}
            />
            {errors.email ? (
              <p className="text-xs text-danger">{errors.email.message}</p>
            ) : null}
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              placeholder="••••••••"
              {...register("password")}
            />
            {errors.password ? (
              <p className="text-xs text-danger">{errors.password.message}</p>
            ) : null}
          </div>
          <Button
            type="submit"
            size="lg"
            className="group w-full"
            disabled={isSubmitting}
          >
            {isSubmitting ? "Signing in…" : "Sign in"}
            <span className="flex size-6 items-center justify-center rounded-full bg-white/15 transition-transform duration-500 ease-silk group-hover:translate-x-0.5">
              <ArrowRight className="size-3.5" strokeWidth={1.75} />
            </span>
          </Button>
        </form>
        <p className="mt-6 text-center text-sm text-muted">
          New here?{" "}
          <Link
            href="/register"
            className="text-foreground underline decoration-white/20 underline-offset-4 transition-colors hover:decoration-accent"
          >
            Create a workspace
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
