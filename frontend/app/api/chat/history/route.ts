import { NextResponse } from "next/server";
import { cookies } from "next/headers";

const API = process.env.API_BASE_URL || "http://localhost:8000";

async function getToken(): Promise<string | null> {
  const cookieStore = await cookies();
  return cookieStore.get("token")?.value ?? null;
}

// GET /api/chat/history — restore persisted conversation
export async function GET() {
  const token = await getToken();
  if (!token) return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });

  const res = await fetch(`${API}/api/chat/history`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const data = await res.json().catch(() => ({ messages: [] }));
  return NextResponse.json(data, { status: res.status });
}

// DELETE /api/chat/history — clear conversation
export async function DELETE() {
  const token = await getToken();
  if (!token) return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });

  const res = await fetch(`${API}/api/chat/history`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });

  // Backend returns 204 No Content
  if (res.status === 204) return new NextResponse(null, { status: 204 });
  const data = await res.json().catch(() => ({}));
  return NextResponse.json(data, { status: res.status });
}
