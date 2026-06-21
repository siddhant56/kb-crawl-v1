import { NextResponse } from "next/server";
import { cookies } from "next/headers";

const API = process.env.API_BASE_URL || "http://localhost:8000";

// GET /api/upload/history — returns the user's uploaded documents (admins see all)
export async function GET() {
  const cookieStore = await cookies();
  const token = cookieStore.get("token")?.value;

  if (!token) return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });

  const res = await fetch(`${API}/api/upload/history`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const data = await res.json().catch(() => ([]));
  return NextResponse.json(data, { status: res.status });
}
