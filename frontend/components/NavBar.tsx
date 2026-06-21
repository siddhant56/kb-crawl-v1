"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { authApi } from "@/lib/api";
import type { UserPublic } from "@/lib/types";
import { Logo } from "./Logo";

export function NavBar() {
  const [user, setUser] = useState<UserPublic | null>(null);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    authApi.me().then(({ ok, data }) => {
      if (ok) setUser(data);
    });
  }, []);

  const logout = async () => {
    await authApi.logout();
    router.push("/login");
  };

  const navLink = (href: string, label: string) => {
    const active = pathname === href;
    return (
      <Link
        href={href}
        className={`text-sm font-medium px-3 py-1.5 rounded-lg transition-colors ${
          active
            ? "bg-indigo-500/10 text-indigo-400"
            : "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800"
        }`}
      >
        {label}
      </Link>
    );
  };

  return (
    <header className="h-14 bg-zinc-900 border-b border-zinc-800 px-5 flex items-center justify-between shrink-0 z-10">
      {/* Left: brand */}
      <div className="flex items-center gap-2.5">
        <Logo size={28} />
        <span className="font-semibold text-zinc-50 tracking-tight">
          Company Expert
        </span>
      </div>

      {/* Right: nav + user */}
      <div className="flex items-center gap-1">
        {navLink("/chat", "Chat")}
        {user?.upload_access && navLink("/upload", "Upload")}
        {user?.role === "super_admin" && navLink("/admin", "Admin")}

        <div className="w-px h-4 bg-zinc-700 mx-2" />

        {user && (
          <span className="text-sm text-zinc-500 hidden sm:block mr-3 truncate max-w-[180px]">
            {user.full_name}
          </span>
        )}
        <button
          onClick={logout}
          className="text-sm text-zinc-400 hover:text-zinc-100 font-medium px-3 py-1.5 rounded-lg hover:bg-zinc-800 transition-colors"
        >
          Sign out
        </button>
      </div>
    </header>
  );
}
