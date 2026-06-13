import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const API = process.env.API_BASE_URL || "http://localhost:8000";

// GET /api/upload/categories — proxy (no auth needed)
export async function GET() {
  const res = await fetch(`${API}/api/upload/categories`);
  const data = await res.json().catch(() => ({ categories: [] }));
  return NextResponse.json(data, { status: res.status });
}

// POST /api/upload — multipart forward with auth cookie
export async function POST(request: NextRequest) {
  const cookieStore = await cookies();
  const token = cookieStore.get("token")?.value;

  if (!token) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  // Forward the multipart body as-is — do NOT set Content-Type manually
  // (the browser sets it with the correct boundary)
  const formData = await request.formData();

  const res = await fetch(`${API}/api/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });

  const data = await res.json().catch(() => ({}));
  return NextResponse.json(data, { status: res.status });
}
