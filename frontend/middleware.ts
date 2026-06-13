/**
 * Edge middleware — runs before every request to protected routes.
 *
 * Reads the httpOnly "token" cookie, verifies the JWT signature locally
 * (using jose — Edge-compatible, no network call), then:
 *   - Unauthenticated → /login
 *   - status ≠ approved on /chat or /admin → /pending
 *   - role ≠ super_admin on /admin → /chat
 *   - Everything else → continue
 */

import { NextRequest, NextResponse } from "next/server";
import { jwtVerify } from "jose";

const PUBLIC_PATHS = ["/login", "/register", "/api/auth/login", "/api/auth/register", "/api/auth/logout", "/api/upload/categories"];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Let public routes through immediately
  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  const token = request.cookies.get("token")?.value;

  if (!token) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  const secret = process.env.AUTH_JWT_SECRET;
  if (!secret) {
    // Misconfigured — fail safe
    console.error("AUTH_JWT_SECRET is not set in the environment.");
    return NextResponse.redirect(new URL("/login", request.url));
  }

  try {
    const { payload } = await jwtVerify(
      token,
      new TextEncoder().encode(secret)
    );

    const userStatus = payload.status as string;
    const role = payload.role as string;
    const uploadAccess = payload.upload_access as boolean | undefined;

    // /api/auth/me and /api/chat and /api/admin/* need auth — already checked above
    // For page routes, enforce business rules:
    if (pathname.startsWith("/admin") && role !== "super_admin") {
      return NextResponse.redirect(new URL("/chat", request.url));
    }

    if (
      (pathname.startsWith("/chat") || pathname.startsWith("/admin") || pathname.startsWith("/upload")) &&
      userStatus !== "approved"
    ) {
      return NextResponse.redirect(new URL("/pending", request.url));
    }

    if (pathname.startsWith("/upload") && !uploadAccess) {
      return NextResponse.redirect(new URL("/chat", request.url));
    }

    return NextResponse.next();
  } catch {
    // Token expired or invalid
    const response = NextResponse.redirect(new URL("/login", request.url));
    response.cookies.delete("token");
    return response;
  }
}

export const config = {
  matcher: [
    /*
     * Match all paths EXCEPT:
     *  - _next/static (static files)
     *  - _next/image (image optimization)
     *  - favicon.ico
     *  - Public auth API routes (handled in PUBLIC_PATHS above)
     */
    "/((?!_next/static|_next/image|favicon.ico).*)",
  ],
};
