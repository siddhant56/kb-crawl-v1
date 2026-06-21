import { NextRequest, NextResponse } from "next/server";

const API = "http://localhost:8000";
console.log(API);

export async function POST(request: NextRequest) {
    const body = await request.json();

    const res = await fetch(`${API}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });

    const data = await res.json();

    if (!res.ok) {
        return NextResponse.json(data, { status: res.status });
    }

    // Set the JWT as an httpOnly cookie so browser JS cannot read it.
    // The token also carries status/role claims — middleware uses these for routing.
    const response = NextResponse.json({ user: data.user }, { status: 200 });
    response.cookies.set("token", data.access_token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        maxAge: 60 * 60 * 24, // 24 hours (match AUTH_TOKEN_EXPIRE_MINUTES)
        path: "/",
    });

    return response;
}
