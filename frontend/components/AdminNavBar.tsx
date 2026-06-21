"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api";
import type { UserPublic } from "@/lib/types";

export function AdminNavBar() {
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
        <header className="h-14 bg-slate-900 px-6 flex items-center justify-between shrink-0">
            {/* Left: title */}
            <div className="flex items-center gap-3">
                <div className="w-7 h-7 rounded bg-blue-500 flex items-center justify-center text-white text-xs font-bold">
                    A
                </div>
                <span className="font-semibold text-white">Admin Panel</span>
            </div>

            {/* Right */}
            <div className="flex items-center gap-4">
                <Link
                    href="/chat"
                    className="text-sm text-slate-300 hover:text-white transition-colors"
                >
                    Chat
                </Link>
                {user && (
                    <span className="text-sm text-slate-400 hidden sm:block">
                        {user.full_name}
                    </span>
                )}
                <button
                    onClick={logout}
                    className="text-sm text-slate-300 hover:text-white font-medium px-3 py-1.5 rounded-lg hover:bg-slate-700 transition-colors"
                >
                    Sign out
                </button>
            </div>
        </header>
    );
}
