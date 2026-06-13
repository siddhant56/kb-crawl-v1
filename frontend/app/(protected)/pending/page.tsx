"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api";
import type { UserPublic } from "@/lib/types";

export default function PendingPage() {
  const [user, setUser] = useState<UserPublic | null>(null);
  const router = useRouter();

  useEffect(() => {
    authApi.me().then(({ ok, data }) => {
      if (!ok) {
        router.push("/login");
        return;
      }
      // If somehow the user is now approved, redirect them
      if (data.status === "approved") {
        router.push(data.role === "super_admin" ? "/admin" : "/chat");
        return;
      }
      setUser(data);
    });
  }, [router]);

  const refresh = async () => {
    const { ok, data } = await authApi.me();
    if (!ok) return;
    if (data.status === "approved") {
      router.push(data.role === "super_admin" ? "/admin" : "/chat");
    }
  };

  const STATUS_INFO: Record<string, { icon: string; headline: string; body: string; color: string }> = {
    pending: {
      icon: "⏳",
      headline: "Awaiting approval",
      body: "Your account has been created. A super admin needs to approve it before you can access the assistant. This usually happens quickly.",
      color: "amber",
    },
    denied: {
      icon: "🚫",
      headline: "Access denied",
      body: "Your access request was declined. Please contact an administrator for more information.",
      color: "red",
    },
    revoked: {
      icon: "⛔",
      headline: "Access revoked",
      body: "Your access has been revoked by an administrator. Please contact them to reinstate access.",
      color: "red",
    },
  };

  const info = user ? STATUS_INFO[user.status] ?? STATUS_INFO.pending : null;
  const colorMap = {
    amber: { bg: "bg-amber-50", border: "border-amber-200", text: "text-amber-800" },
    red: { bg: "bg-red-50", border: "border-red-200", text: "text-red-800" },
  };
  const colors = info ? colorMap[info.color as keyof typeof colorMap] : colorMap.amber;

  return (
    <div className="h-full flex items-center justify-center px-4">
      <div className="w-full max-w-md text-center">
        <div
          className={`${colors.bg} ${colors.border} border rounded-2xl p-8`}
        >
          <div className="text-5xl mb-4">{info?.icon ?? "⏳"}</div>
          <h2 className={`text-xl font-bold ${colors.text} mb-2`}>
            {info?.headline ?? "Account pending"}
          </h2>
          <p className="text-gray-600 text-sm mb-6">{info?.body}</p>

          {user?.email && (
            <p className="text-xs text-gray-400 mb-6">
              Signed in as <strong>{user.email}</strong>
            </p>
          )}

          <div className="flex gap-3 justify-center">
            {user?.status === "pending" && (
              <button
                onClick={refresh}
                className="text-sm bg-white border border-gray-300 hover:border-gray-400 text-gray-700 font-medium px-4 py-2 rounded-lg transition-colors"
              >
                Check status
              </button>
            )}
            <button
              onClick={async () => {
                await authApi.logout();
                router.push("/login");
              }}
              className="text-sm bg-gray-900 hover:bg-gray-700 text-white font-medium px-4 py-2 rounded-lg transition-colors"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
