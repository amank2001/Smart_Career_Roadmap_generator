import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import { AuthGuard } from "@/components/layout/AuthGuard";
import { DashboardLayout } from "@/components/layout/DashboardLayout";

export const metadata: Metadata = {
  title: "Smart Career Roadmap Generator",
  description: "Plan your career transition with AI-powered roadmaps",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        <AuthProvider>
          <AuthGuard>
            <DashboardLayout>{children}</DashboardLayout>
          </AuthGuard>
        </AuthProvider>
      </body>
    </html>
  );
}
