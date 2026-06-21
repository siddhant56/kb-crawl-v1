"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { authApi, extractError } from "@/lib/api";
import { Logo } from "@/components/Logo";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const { ok, data } = await authApi.login(email.trim(), password);
    setLoading(false);

    if (!ok) {
      setError(extractError(data));
      return;
    }

    const user = (data as { user: { status: string; role: string } }).user;
    if (user.status !== "approved") {
      router.push("/pending");
    } else if (user.role === "super_admin") {
      router.push("/admin");
    } else {
      router.push("/chat");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-950 px-4">
      {/* Subtle radial glow behind the card */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-indigo-600/5 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-sm">
        {/* Logo + headline */}
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <Logo size={44} />
          </div>
          <h1 className="text-2xl font-bold text-zinc-50 tracking-tight">
            Welcome back
          </h1>
          <p className="text-zinc-500 text-sm mt-1.5">
            Sign in to Company Expert
          </p>
        </div>

        {/* Card */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-8 shadow-xl shadow-black/40">
          <form onSubmit={submit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1.5">
                Email
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                className="w-full input-dark px-3.5 py-2.5 text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1.5">
                Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full input-dark px-3.5 py-2.5 text-sm"
              />
            </div>

            {error && (
              <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 text-sm text-red-400">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full gradient-brand hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-2.5 px-4 rounded-lg text-sm transition-opacity flex items-center justify-center gap-2 mt-1"
            >
              {loading ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Signing in…
                </>
              ) : (
                "Sign in"
              )}
            </button>
          </form>
        </div>

        <p className="text-center text-sm text-zinc-600 mt-6">
          Don&apos;t have an account?{" "}
          <Link
            href="/register"
            className="text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
          >
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
