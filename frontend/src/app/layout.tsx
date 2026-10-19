import type { Metadata } from "next";
import localFont from "next/font/local";
import { Toaster } from "sonner";

import { AuthProvider } from "@/lib/auth";

import "./globals.css";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "ShiftSathi — Frontline operations assistant",
  description:
    "AI-grounded maintenance knowledge, incidents and work orders for frontline teams.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <AuthProvider>{children}</AuthProvider>
        <Toaster
          theme="dark"
          position="bottom-right"
          toastOptions={{
            style: {
              background: "rgba(11,11,15,0.95)",
              border: "1px solid rgba(255,255,255,0.1)",
              color: "#f4f4f6",
              borderRadius: "1rem",
              backdropFilter: "blur(16px)",
            },
          }}
        />
      </body>
    </html>
  );
}
