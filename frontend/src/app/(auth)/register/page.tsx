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
  organization_name: z
    .string()
    .min(2, "Organization name is too short.")
    .max(200),
  full_name: z.string().min(2, "Your name is too short.").max(200),
  email: z.string().email("Enter a valid email address."),
  password: z
    .string()
    .min(8, "Use at least 8 characters.")
    .regex(/[A-Za-z]/, "Include at least one letter.")
    .regex(/\d/, "Include at least one number."),
});

type FormValues = z.infer<typeof schema>;

export default function RegisterPage() {
  const { register: registerUser } = useAuth();
  const router = useRouter();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      organization_name: "",
      full_name: "",
      email: "",
      password: "",
    },
  });

  async function onSubmit(values: FormValues) {
    try {
      await registerUser(values);
      toast.success("Workspace created");
      router.replace("/dashboard");
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? err.message
          : "Unable to create the workspace right now.",
      );
    }
  }

  const fields = [
    {
      name: "organization_name" as const,
      label: "Organization name",
      type: "text",
      placeholder: "Karakoram Textiles",
      autoComplete: "organization",
    },
    {
      name: "full_name" as const,
      label: "Your name",
      type: "text",
      placeholder: "Ayesha Khan",
      autoComplete: "name",
    },
    {
      name: "email" as const,
      label: "Work email",
      type: "email",
      placeholder: "you@factory.pk",
      autoComplete: "email",
    },
    {
      name: "password" as const,
      label: "Password",
      type: "password",
      placeholder: "Minimum 8 characters",
      autoComplete: "new-password",
    },
  ];

  return (
    <Card className="w-full max-w-md">
      <CardContent className="p-7">
        <CardHeader className="px-0 pt-0">
          <CardTitle className="text-2xl">Create your workspace</CardTitle>
          <CardDescription>
            You become the first admin for this organization.
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          {fields.map((field) => (
            <div key={field.name} className="space-y-2">
              <Label htmlFor={field.name}>{field.label}</Label>
              <Input
                id={field.name}
                type={field.type}
                autoComplete={field.autoComplete}
                placeholder={field.placeholder}
                {...register(field.name)}
              />
              {errors[field.name] ? (
                <p className="text-xs text-danger">
                  {errors[field.name]?.message}
                </p>
              ) : null}
            </div>
          ))}
          <Button
            type="submit"
            size="lg"
            className="group w-full"
            disabled={isSubmitting}
          >
            {isSubmitting ? "Creating…" : "Create workspace"}
            <span className="flex size-6 items-center justify-center rounded-full bg-white/15 transition-transform duration-500 ease-silk group-hover:translate-x-0.5">
              <ArrowRight className="size-3.5" strokeWidth={1.75} />
            </span>
          </Button>
        </form>
        <p className="mt-6 text-center text-sm text-muted">
          Already have a workspace?{" "}
          <Link
            href="/login"
            className="text-foreground underline decoration-white/20 underline-offset-4 transition-colors hover:decoration-accent"
          >
            Sign in
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
