"use client";

import { usePathname } from "next/navigation";
import { Sidebar } from "./Sidebar";
import { MobileNav } from "./MobileNav";

const AUTH_ROUTES = ["/login", "/register"];

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const pathname = usePathname();
  const isAuthRoute = AUTH_ROUTES.includes(pathname);

  // Auth pages get a clean layout without sidebar
  if (isAuthRoute) {
    return (
      <div className="min-h-screen bg-gray-50">
        <main>
          <div className="mx-auto max-w-5xl px-4 py-8">
            {children}
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Desktop sidebar */}
      <div className="hidden lg:block">
        <Sidebar />
      </div>

      {/* Mobile navigation */}
      <MobileNav />

      {/* Main content */}
      <main className="lg:pl-64">
        <div className="mx-auto max-w-5xl px-4 py-8 pt-20 lg:px-8 lg:pt-8">
          {children}
        </div>
      </main>
    </div>
  );
}
