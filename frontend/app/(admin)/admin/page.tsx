"use client";

import { useEffect, useState, useCallback } from "react";
import { adminApi, authApi, extractError } from "@/lib/api";
import type { AdminStats, UserAdmin, UserStatus } from "@/lib/types";

// ─── Status badge ─────────────────────────────────────────────────────────────
const STATUS_STYLES: Record<UserStatus, string> = {
  pending:  "bg-amber-500/10 text-amber-400 border-amber-500/20",
  approved: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  denied:   "bg-red-500/10 text-red-400 border-red-500/20",
  revoked:  "bg-zinc-700/40 text-zinc-500 border-zinc-700",
};

function StatusBadge({ status }: { status: UserStatus }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium capitalize border ${STATUS_STYLES[status]}`}>
      {status}
    </span>
  );
}

// ─── Stats cards ──────────────────────────────────────────────────────────────
function StatsBar({ stats }: { stats: AdminStats | null }) {
  const cards = [
    { label: "Total users", value: stats?.total ?? "—", accent: "indigo" },
    { label: "Pending", value: stats?.by_status.pending ?? 0, accent: "amber" },
    { label: "Approved", value: stats?.by_status.approved ?? 0, accent: "emerald" },
    { label: "Denied", value: stats?.by_status.denied ?? 0, accent: "red" },
    { label: "Revoked", value: stats?.by_status.revoked ?? 0, accent: "zinc" },
  ];

  const accent: Record<string, string> = {
    indigo: "text-indigo-400",
    amber:  "text-amber-400",
    emerald:"text-emerald-400",
    red:    "text-red-400",
    zinc:   "text-zinc-500",
  };

  return (
    <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-6">
      {cards.map((c) => (
        <div key={c.label} className="bg-zinc-900 border border-zinc-800 rounded-xl px-5 py-4">
          <p className="text-xs text-zinc-600 mb-1">{c.label}</p>
          <p className={`text-2xl font-bold ${accent[c.accent]}`}>{c.value}</p>
        </div>
      ))}
    </div>
  );
}

// ─── Deny modal ───────────────────────────────────────────────────────────────
function DenyModal({ user, onConfirm, onCancel }: { user: UserAdmin; onConfirm: (r: string) => void; onCancel: () => void }) {
  const [reason, setReason] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const confirm = () => {
    if (reason.trim().length < 5) { setErr("Please provide a reason of at least 5 characters."); return; }
    onConfirm(reason.trim());
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 px-4">
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl shadow-2xl shadow-black/60 w-full max-w-md p-6">
        <h3 className="text-base font-semibold text-zinc-100 mb-1">Deny access for {user.full_name}</h3>
        <p className="text-sm text-zinc-500 mb-4">Provide a reason. This is stored on the user record.</p>
        <textarea
          rows={3}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="e.g. Unrecognised email domain, not an employee…"
          className="w-full input-dark px-3.5 py-2.5 text-sm resize-none"
        />
        {err && <p className="text-sm text-red-400 mt-2">{err}</p>}
        <div className="flex gap-3 mt-5 justify-end">
          <button
            onClick={onCancel}
            className="text-sm text-zinc-400 hover:text-zinc-200 font-medium px-4 py-2 rounded-lg hover:bg-zinc-800 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={confirm}
            className="text-sm bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-400 font-medium px-4 py-2 rounded-lg transition-colors"
          >
            Deny access
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Action button ────────────────────────────────────────────────────────────
function ActionBtn({ label, onClick, variant = "default" }: { label: string; onClick: () => void; variant?: string }) {
  const styles: Record<string, string> = {
    default:  "border border-zinc-700 text-zinc-400 hover:text-zinc-200 hover:border-zinc-600 hover:bg-zinc-800",
    approve:  "border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10",
    deny:     "border border-red-500/30 text-red-400 hover:bg-red-500/10",
    revoke:   "border border-amber-500/30 text-amber-400 hover:bg-amber-500/10",
    promote:  "border border-indigo-500/30 text-indigo-400 hover:bg-indigo-500/10",
    demote:   "border border-zinc-600 text-zinc-500 hover:text-zinc-300 hover:border-zinc-500",
    upload:   "border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10",
    "revoke-upload": "border border-orange-500/30 text-orange-400 hover:bg-orange-500/10",
    delete:   "text-red-500 hover:text-red-300 hover:bg-red-500/10",
  };

  return (
    <button
      onClick={onClick}
      className={`text-[11px] font-medium px-2.5 py-1 rounded-lg transition-colors ${styles[variant] ?? styles.default}`}
    >
      {label}
    </button>
  );
}

// ─── User row ─────────────────────────────────────────────────────────────────
function UserRow({ user, currentUserId, onAction }: { user: UserAdmin; currentUserId?: number; onAction: (a: string, u: UserAdmin) => void }) {
  const isSelf = user.id === currentUserId;

  const joined = new Date(user.created_at).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });

  const initials = user.full_name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2);

  return (
    <tr className="border-b border-zinc-800/60 hover:bg-zinc-800/30 transition-colors">
      {/* User info */}
      <td className="px-4 py-3.5">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg gradient-brand flex items-center justify-center shrink-0">
            <span className="text-xs font-bold text-white">{initials}</span>
          </div>
          <div>
            <p className="text-sm font-medium text-zinc-200">
              {user.full_name}
              {isSelf && <span className="ml-1.5 text-xs text-zinc-600">(you)</span>}
            </p>
            <p className="text-xs text-zinc-500">{user.email}</p>
          </div>
        </div>
      </td>

      {/* Role */}
      <td className="px-4 py-3.5">
        <div className="flex flex-col gap-1">
          <span className={`text-[11px] font-medium px-2 py-0.5 rounded border w-fit ${
            user.role === "super_admin"
              ? "bg-indigo-500/10 text-indigo-400 border-indigo-500/20"
              : "bg-zinc-800 text-zinc-500 border-zinc-700"
          }`}>
            {user.role === "super_admin" ? "Super Admin" : "User"}
          </span>
          {user.upload_access && (
            <span className="text-[11px] font-medium px-2 py-0.5 rounded border w-fit bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
              Upload
            </span>
          )}
        </div>
      </td>

      {/* Status */}
      <td className="px-4 py-3.5">
        <StatusBadge status={user.status} />
        {user.status === "denied" && user.denial_reason && (
          <p className="text-xs text-zinc-600 mt-1 max-w-[180px] truncate" title={user.denial_reason}>
            {user.denial_reason}
          </p>
        )}
      </td>

      {/* Joined */}
      <td className="px-4 py-3.5 text-xs text-zinc-600 whitespace-nowrap">{joined}</td>

      {/* Actions */}
      <td className="px-4 py-3.5">
        {isSelf ? (
          <span className="text-xs text-zinc-700">—</span>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {user.status !== "approved" && user.role !== "super_admin" && (
              <ActionBtn label="Approve" variant="approve" onClick={() => onAction("approve", user)} />
            )}
            {user.status === "pending" && user.role !== "super_admin" && (
              <ActionBtn label="Deny" variant="deny" onClick={() => onAction("deny", user)} />
            )}
            {user.status === "approved" && user.role !== "super_admin" && (
              <ActionBtn label="Revoke" variant="revoke" onClick={() => onAction("revoke", user)} />
            )}
            {user.role !== "super_admin" && (
              <ActionBtn label="Make Admin" variant="promote" onClick={() => onAction("promote", user)} />
            )}
            {user.role === "super_admin" && (
              <ActionBtn label="Remove Admin" variant="demote" onClick={() => onAction("demote", user)} />
            )}
            {user.status === "approved" && user.role !== "super_admin" && !user.upload_access && (
              <ActionBtn label="Grant Upload" variant="upload" onClick={() => onAction("grant-upload", user)} />
            )}
            {user.status === "approved" && user.role !== "super_admin" && user.upload_access && (
              <ActionBtn label="Revoke Upload" variant="revoke-upload" onClick={() => onAction("revoke-upload", user)} />
            )}
            {(user.status === "denied" || user.status === "revoked") && user.role !== "super_admin" && (
              <ActionBtn label="Delete" variant="delete" onClick={() => onAction("delete", user)} />
            )}
          </div>
        )}
      </td>
    </tr>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
type TabFilter = "all" | UserStatus;

export default function AdminPage() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<UserAdmin[]>([]);
  const [currentUserId, setCurrentUserId] = useState<number | undefined>();
  const [tab, setTab] = useState<TabFilter>("all");
  const [loading, setLoading] = useState(true);
  const [actionError, setActionError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [denyTarget, setDenyTarget] = useState<UserAdmin | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    const [statsRes, usersRes, meRes] = await Promise.all([
      adminApi.getStats(), adminApi.getUsers({ limit: 200 }), authApi.me(),
    ]);
    if (statsRes.ok) setStats(statsRes.data);
    if (usersRes.ok) setUsers(usersRes.data);
    if (meRes.ok) setCurrentUserId(meRes.data.id);
    setLoading(false);
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const showSuccess = (msg: string) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(null), 3000);
  };

  const handleAction = async (action: string, user: UserAdmin) => {
    setActionError(null);
    if (action === "deny") { setDenyTarget(user); return; }

    let result;
    switch (action) {
      case "approve":      result = await adminApi.approve(user.id); break;
      case "revoke":       result = await adminApi.revoke(user.id); break;
      case "promote":      result = await adminApi.changeRole(user.id, "super_admin"); break;
      case "demote":       result = await adminApi.changeRole(user.id, "user"); break;
      case "grant-upload": result = await adminApi.grantUpload(user.id); break;
      case "revoke-upload":result = await adminApi.revokeUpload(user.id); break;
      case "delete":
        if (!confirm(`Permanently delete ${user.full_name}? This cannot be undone.`)) return;
        result = await adminApi.deleteUser(user.id);
        break;
      default: return;
    }

    if (!result.ok) { setActionError(extractError(result.data)); return; }
    showSuccess(`${user.full_name} — ${action} successful.`);
    fetchData();
  };

  const handleDenyConfirm = async (reason: string) => {
    if (!denyTarget) return;
    const result = await adminApi.deny(denyTarget.id, reason);
    setDenyTarget(null);
    if (!result.ok) { setActionError(extractError(result.data)); return; }
    showSuccess(`${denyTarget.full_name} — access denied.`);
    fetchData();
  };

  const TABS: { key: TabFilter; label: string }[] = [
    { key: "all", label: "All" },
    { key: "pending", label: "Pending" },
    { key: "approved", label: "Approved" },
    { key: "denied", label: "Denied" },
    { key: "revoked", label: "Revoked" },
  ];

  const filteredUsers = tab === "all" ? users : users.filter((u) => u.status === tab);

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-zinc-50 tracking-tight">User Management</h1>
        <p className="text-zinc-500 text-sm mt-1">
          Approve, deny, or revoke access to Company Expert.
        </p>
      </div>

      <StatsBar stats={stats} />

      {/* Tabs */}
      <div className="flex gap-1 mb-4 bg-zinc-900 border border-zinc-800 rounded-xl p-1 w-fit">
        {TABS.map((t) => {
          const count = t.key === "all" ? stats?.total ?? 0 : (stats?.by_status[t.key] ?? 0);
          return (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`text-sm px-3.5 py-1.5 rounded-lg font-medium transition-colors flex items-center gap-1.5 ${
                tab === t.key
                  ? "gradient-brand text-white shadow-sm"
                  : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800"
              }`}
            >
              {t.label}
              {count > 0 && (
                <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                  tab === t.key ? "bg-white/20 text-white" : "bg-zinc-800 text-zinc-500"
                }`}>
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Toast messages */}
      {successMsg && (
        <div className="mb-4 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm px-4 py-3 rounded-xl">
          ✓ {successMsg}
        </div>
      )}
      {actionError && (
        <div className="mb-4 bg-red-500/10 border border-red-500/20 text-red-400 text-sm px-4 py-3 rounded-xl flex justify-between">
          <span>{actionError}</span>
          <button onClick={() => setActionError(null)} className="text-red-500 hover:text-red-300 ml-4">✕</button>
        </div>
      )}

      {/* Table */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <span className="w-6 h-6 border-2 border-zinc-700 border-t-indigo-500 rounded-full animate-spin" />
          </div>
        ) : filteredUsers.length === 0 ? (
          <div className="text-center py-16 text-zinc-600 text-sm">
            No {tab !== "all" ? tab : ""} users found.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-zinc-800">
                  {["User", "Role", "Status", "Joined", "Actions"].map((h) => (
                    <th key={h} className="px-4 py-3 text-[11px] font-semibold text-zinc-600 uppercase tracking-wider">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map((u) => (
                  <UserRow key={u.id} user={u} currentUserId={currentUserId} onAction={handleAction} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <p className="text-xs text-zinc-700 mt-4 text-center">
        {filteredUsers.length} user{filteredUsers.length !== 1 ? "s" : ""}{" "}
        {tab !== "all" ? `with status "${tab}"` : "total"}
      </p>

      {denyTarget && (
        <DenyModal user={denyTarget} onConfirm={handleDenyConfirm} onCancel={() => setDenyTarget(null)} />
      )}
    </div>
  );
}
