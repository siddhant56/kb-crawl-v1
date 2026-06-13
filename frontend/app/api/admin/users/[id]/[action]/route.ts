import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const API = process.env.API_BASE_URL || "http://localhost:8000";

// PATCH /api/admin/users/[id]/[action]
// action: approve | deny | revoke | role
export async function PATCH(
  request: NextRequest,
  { params }: { params: { id: string; action: string } }
) {
  const cookieStore = await cookies();
  const token = cookieStore.get("token")?.value;

  if (!token) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  // Body may be empty (approve, revoke) or contain {reason} or {role}
  let body: string | undefined;
  try {
    const json = await request.json();
    body = JSON.stringify(json);
  } catch {
    body = undefined;
  }

  const res = await fetch(
    `${API}/auth/admin/users/${params.id}/${params.action}`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body,
    }
  );

  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
