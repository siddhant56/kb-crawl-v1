"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api";
import type { UserPublic } from "@/lib/types";

export function NavBar() {
  const [user, setUser] = useState<UserPublic | null>(null);
  const router = useRouter();

  useEffect(() => {
    authApi.me().then(({ ok, data }) => {
      if (ok) setUser(data);
    });
  }, []);

  const logout = async () => {
    await authApi.logout();
    router.push("/login");
  };

  return (
    <header className="h-14 bg-white border-b border-gray-200 px-4 flex items-center justify-between shrink-0 z-10">
      {/* Left: brand */}
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white text-sm font-bold">
          C
        </div>
        <span className="font-semibold text-gray-900">Company Expert</span>
      </div>

      {/* Right: nav links + user info */}
      <div className="flex items-center gap-4">
        {user?.role === "super_admin" && (
          <Link
            href="/admin"
            className="text-sm text-blue-600 hover:text-blue-700 font-medium"
          >
            Admin Panel
          </Link>
        )}
        {user && (
          <span className="text-sm text-gray-500 hidden sm:block">
            {user.full_name}
          </span>
        )}
        <button
          onClick={logout}
          className="text-sm text-gray-600 hover:text-gray-900 font-medium px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-colors"
        >
          Sign out
        </button>
      </div>
    </header>
  );
}
