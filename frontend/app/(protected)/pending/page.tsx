"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api";
import type { UserPublic } from "@/lib/types";
import { Logo } from "@/components/Logo";

export default function PendingPage() {
  const [user, setUser] = useState<UserPublic | null>(null);
  const router = useRouter();

  useEffect(() => {
    authApi.me().then(({ ok, data }) => {
      if (!ok) { router.push("/login"); return; }
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

  type StatusKey = "pending" | "denied" | "revoked";

  const STATUS_INFO: Record<StatusKey, { headline: string; body: string; accent: string }> = {
    pending: {
      headline: "Awaiting approval",
      body: "Your account has been created. A super admin needs to approve it before you can access the assistant.",
      accent: "amber",
    },
    denied: {
      headline: "Access denied",
      body: "Your access request was declined. Please contact an administrator for more information.",
      accent: "red",
    },
    revoked: {
      headline: "Access revoked",
      body: "Your access has been revoked by an administrator. Please contact them to reinstate access.",
      accent: "red",
    },
  };

  const info = user ? (STATUS_INFO[user.status as StatusKey] ?? STATUS_INFO.pending) : null;
  const isAmber = info?.accent === "amber";

  const iconBg = isAmber ? "bg-amber-500/10 border-amber-500/20" : "bg-red-500/10 border-red-500/20";
  const iconColor = isAmber ? "text-amber-400" : "text-red-400";
  const cardBorder = isAmber ? "border-amber-500/20" : "border-red-500/20";
  const headlineColor = isAmber ? "text-amber-300" : "text-red-300";

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-950 px-4">
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className={`absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] ${isAmber ? "bg-amber-600/5" : "bg-red-600/5"} rounded-full blur-3xl`} />
      </div>

      <div className="relative w-full max-w-md text-center">
        <div className="mb-6 flex justify-center">
          <Logo size={44} />
        </div>

        <div className={`bg-zinc-900 border ${cardBorder} rounded-2xl p-8 shadow-xl shadow-black/40`}>
          <div className={`w-14 h-14 rounded-2xl border ${iconBg} flex items-center justify-center mx-auto mb-5`}>
            {isAmber ? (
              <svg className={`w-7 h-7 ${iconColor}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            ) : (
              <svg className={`w-7 h-7 ${iconColor}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
              </svg>
            )}
          </div>

          <h2 className={`text-xl font-bold ${headlineColor} mb-2 tracking-tight`}>
            {info?.headline ?? "Account pending"}
          </h2>
          <p className="text-zinc-500 text-sm mb-6 leading-relaxed">{info?.body}</p>

          {user?.email && (
            <p className="text-xs text-zinc-600 mb-6">
              Signed in as <span className="text-zinc-400 font-medium">{user.email}</span>
            </p>
          )}

          <div className="flex gap-3 justify-center">
            {user?.status === "pending" && (
              <button
                onClick={refresh}
                className="text-sm bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-300 font-medium px-4 py-2 rounded-lg transition-colors"
              >
                Check status
              </button>
            )}
            <button
              onClick={async () => { await authApi.logout(); router.push("/login"); }}
              className="text-sm gradient-brand hover:opacity-90 text-white font-medium px-4 py-2 rounded-lg transition-opacity"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
