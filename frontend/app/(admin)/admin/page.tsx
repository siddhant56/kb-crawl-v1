"use client";

import { useEffect, useState, useCallback } from "react";
import { adminApi, authApi, extractError } from "@/lib/api";
import type { AdminStats, UserAdmin, UserStatus } from "@/lib/types";

// ─── Status badge ─────────────────────────────────────────────────────────────
const STATUS_STYLES: Record<UserStatus, string> = {
  pending: "bg-amber-100 text-amber-800",
  approved: "bg-green-100 text-green-800",
  denied: "bg-red-100 text-red-800",
  revoked: "bg-gray-200 text-gray-700",
};

function StatusBadge({ status }: { status: UserStatus }) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${STATUS_STYLES[status]}`}
    >
      {status}
    </span>
  );
}

// ─── Stats cards ──────────────────────────────────────────────────────────────
function StatsBar({ stats }: { stats: AdminStats | null }) {
  const cards = [
    { label: "Total", value: stats?.total ?? "—", color: "text-gray-900" },
    { label: "Pending", value: stats?.by_status.pending ?? 0, color: "text-amber-600" },
    { label: "Approved", value: stats?.by_status.approved ?? 0, color: "text-green-600" },
    { label: "Denied", value: stats?.by_status.denied ?? 0, color: "text-red-600" },
    { label: "Revoked", value: stats?.by_status.revoked ?? 0, color: "text-gray-500" },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 mb-6">
      {cards.map((c) => (
        <div key={c.label} className="bg-white rounded-xl border border-gray-200 px-5 py-4">
          <p className="text-xs text-gray-500 mb-1">{c.label}</p>
          <p className={`text-2xl font-bold ${c.color}`}>{c.value}</p>
        </div>
      ))}
    </div>
  );
}

// ─── Deny modal ───────────────────────────────────────────────────────────────
function DenyModal({
  user,
  onConfirm,
  onCancel,
}: {
  user: UserAdmin;
  onConfirm: (reason: string) => void;
  onCancel: () => void;
}) {
  const [reason, setReason] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const confirm = () => {
    if (reason.trim().length < 5) {
      setErr("Please provide a reason of at least 5 characters.");
      return;
    }
    onConfirm(reason.trim());
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-1">
          Deny access for {user.full_name}
        </h3>
        <p className="text-sm text-gray-500 mb-4">
          Provide a reason. This is stored on the user record.
        </p>
        <textarea
          rows={3}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="e.g. Unrecognised email domain, not an employee…"
          className="w-full border border-gray-300 rounded-lg px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-500 resize-none"
        />
        {err && <p className="text-sm text-red-600 mt-2">{err}</p>}
        <div className="flex gap-3 mt-5 justify-end">
          <button
            onClick={onCancel}
            className="text-sm text-gray-600 hover:text-gray-900 font-medium px-4 py-2 rounded-lg hover:bg-gray-100 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={confirm}
            className="text-sm bg-red-600 hover:bg-red-700 text-white font-medium px-4 py-2 rounded-lg transition-colors"
          >
            Deny access
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── User row ─────────────────────────────────────────────────────────────────
function UserRow({
  user,
  currentUserId,
  onAction,
}: {
  user: UserAdmin;
  currentUserId?: number;
  onAction: (action: string, user: UserAdmin) => void;
}) {
  const isSelf = user.id === currentUserId;

  const joined = new Date(user.created_at).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  const initials = user.full_name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <tr className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
      {/* User info */}
      <td className="px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
            <span className="text-xs font-bold text-blue-700">{initials}</span>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-900">
              {user.full_name}
              {isSelf && (
                <span className="ml-1.5 text-xs text-gray-400">(you)</span>
              )}
            </p>
            <p className="text-xs text-gray-500">{user.email}</p>
          </div>
        </div>
      </td>

      {/* Role */}
      <td className="px-4 py-3">
        <span
          className={`text-xs font-medium px-2 py-0.5 rounded ${
            user.role === "super_admin"
              ? "bg-purple-100 text-purple-800"
              : "bg-gray-100 text-gray-700"
          }`}
        >
          {user.role === "super_admin" ? "Super Admin" : "User"}
        </span>
      </td>

      {/* Status */}
      <td className="px-4 py-3">
        <StatusBadge status={user.status} />
        {user.status === "denied" && user.denial_reason && (
          <p className="text-xs text-gray-400 mt-1 max-w-[200px] truncate" title={user.denial_reason}>
            {user.denial_reason}
          </p>
        )}
      </td>

      {/* Joined */}
      <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
        {joined}
      </td>

      {/* Actions */}
      <td className="px-4 py-3">
        {isSelf ? (
          <span className="text-xs text-gray-400">—</span>
        ) : (
          <div className="flex flex-wrap gap-2">
            {user.status !== "approved" && user.role !== "super_admin" && (
              <button
                onClick={() => onAction("approve", user)}
                className="text-xs bg-green-600 hover:bg-green-700 text-white px-2.5 py-1 rounded-lg font-medium transition-colors"
              >
                Approve
              </button>
            )}
            {user.status === "pending" && user.role !== "super_admin" && (
              <button
                onClick={() => onAction("deny", user)}
                className="text-xs bg-red-600 hover:bg-red-700 text-white px-2.5 py-1 rounded-lg font-medium transition-colors"
              >
                Deny
              </button>
            )}
            {user.status === "approved" && user.role !== "super_admin" && (
              <button
                onClick={() => onAction("revoke", user)}
                className="text-xs bg-amber-500 hover:bg-amber-600 text-white px-2.5 py-1 rounded-lg font-medium transition-colors"
              >
                Revoke
              </button>
            )}
            {user.role !== "super_admin" && (
              <button
                onClick={() => onAction("promote", user)}
                className="text-xs border border-purple-300 hover:bg-purple-50 text-purple-700 px-2.5 py-1 rounded-lg font-medium transition-colors"
              >
                Make Admin
              </button>
            )}
            {user.role === "super_admin" && (
              <button
                onClick={() => onAction("demote", user)}
                className="text-xs border border-gray-300 hover:bg-gray-50 text-gray-600 px-2.5 py-1 rounded-lg font-medium transition-colors"
              >
                Remove Admin
              </button>
            )}
            {(user.status === "denied" || user.status === "revoked") && user.role !== "super_admin" && (
              <button
                onClick={() => onAction("delete", user)}
                className="text-xs text-red-500 hover:text-red-700 hover:bg-red-50 px-2.5 py-1 rounded-lg font-medium transition-colors"
              >
                Delete
              </button>
            )}
          </div>
        )}
      </td>
    </tr>
  );
}

// ─── Main admin page ──────────────────────────────────────────────────────────
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
      adminApi.getStats(),
      adminApi.getUsers({ limit: 200 }),
      authApi.me(),
    ]);
    if (statsRes.ok) setStats(statsRes.data);
    if (usersRes.ok) setUsers(usersRes.data);
    if (meRes.ok) setCurrentUserId(meRes.data.id);
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const showSuccess = (msg: string) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(null), 3000);
  };

  const handleAction = async (action: string, user: UserAdmin) => {
    setActionError(null);

    if (action === "deny") {
      setDenyTarget(user);
      return;
    }

    let result;
    switch (action) {
      case "approve":
        result = await adminApi.approve(user.id);
        break;
      case "revoke":
        result = await adminApi.revoke(user.id);
        break;
      case "promote":
        result = await adminApi.changeRole(user.id, "super_admin");
        break;
      case "demote":
        result = await adminApi.changeRole(user.id, "user");
        break;
      case "delete":
        if (!confirm(`Permanently delete ${user.full_name}? This cannot be undone.`)) return;
        result = await adminApi.deleteUser(user.id);
        break;
      default:
        return;
    }

    if (!result.ok) {
      setActionError(extractError(result.data));
      return;
    }

    showSuccess(`${user.full_name} — ${action} successful.`);
    fetchData();
  };

  const handleDenyConfirm = async (reason: string) => {
    if (!denyTarget) return;
    const result = await adminApi.deny(denyTarget.id, reason);
    setDenyTarget(null);
    if (!result.ok) {
      setActionError(extractError(result.data));
      return;
    }
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

  const filteredUsers =
    tab === "all" ? users : users.filter((u) => u.status === tab);

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">User Management</h1>
        <p className="text-gray-500 text-sm mt-1">
          Approve, deny, or revoke access to the Company Expert chatbot.
        </p>
      </div>

      <StatsBar stats={stats} />

      {/* Tabs */}
      <div className="flex gap-1 mb-4 bg-white border border-gray-200 rounded-xl p-1 w-fit">
        {TABS.map((t) => {
          const count =
            t.key === "all"
              ? stats?.total ?? 0
              : (stats?.by_status[t.key] ?? 0);
          return (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`text-sm px-3.5 py-1.5 rounded-lg font-medium transition-colors flex items-center gap-1.5 ${
                tab === t.key
                  ? "bg-gray-900 text-white"
                  : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
              }`}
            >
              {t.label}
              {count > 0 && (
                <span
                  className={`text-xs px-1.5 py-0.5 rounded-full ${
                    tab === t.key ? "bg-white/20 text-white" : "bg-gray-100 text-gray-600"
                  }`}
                >
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Toast messages */}
      {successMsg && (
        <div className="mb-4 bg-green-50 border border-green-200 text-green-800 text-sm px-4 py-3 rounded-xl">
          ✓ {successMsg}
        </div>
      )}
      {actionError && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-xl flex justify-between">
          <span>{actionError}</span>
          <button onClick={() => setActionError(null)} className="text-red-400 hover:text-red-600 ml-4">✕</button>
        </div>
      )}

      {/* User table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <span className="w-6 h-6 border-2 border-gray-300 border-t-blue-600 rounded-full animate-spin" />
          </div>
        ) : filteredUsers.length === 0 ? (
          <div className="text-center py-16 text-gray-400">
            No {tab !== "all" ? tab : ""} users found.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  {["User", "Role", "Status", "Joined", "Actions"].map((h) => (
                    <th
                      key={h}
                      className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map((u) => (
                  <UserRow
                    key={u.id}
                    user={u}
                    currentUserId={currentUserId}
                    onAction={handleAction}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <p className="text-xs text-gray-400 mt-4 text-center">
        {filteredUsers.length} user{filteredUsers.length !== 1 ? "s" : ""}{" "}
        {tab !== "all" ? `with status "${tab}"` : "total"}
      </p>

      {/* Deny modal */}
      {denyTarget && (
        <DenyModal
          user={denyTarget}
          onConfirm={handleDenyConfirm}
          onCancel={() => setDenyTarget(null)}
        />
      )}
    </div>
  );
}
