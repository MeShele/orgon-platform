import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  // Public routes — never require auth.
  const publicRoutes = ['/', '/login', '/register', '/features', '/pricing', '/about', '/forgot-password', '/reset-password', '/demo'];
  const isPublicRoute = publicRoutes.some(route => pathname === route || pathname.startsWith(route + '/'));

  const accessToken = request.cookies.get('orgon_access_token')?.value;

  // Unauthenticated → bounce to /login with `next=` so user lands back where
  // they tried to go after authenticating.
  if (!accessToken && !isPublicRoute) {
    const url = new URL('/login', request.url);
    url.searchParams.set('next', pathname + search);
    return NextResponse.redirect(url);
  }

  // Authenticated user on /login or /register → straight to dashboard.
  if (accessToken && (pathname === '/login' || pathname === '/register')) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api  (operator API — auth handled at backend, no /login redirect)
     * - v1   (B2B merchant API — HMAC-signed; integrators MUST get a
     *         JSON envelope from the backend, never an HTML redirect)
     * - ws   (WebSocket — redirecting to /login breaks the upgrade handshake)
     * - _next/static / _next/image (assets)
     * - favicon.ico
     * - public assets (.png/.jpg/.jpeg/.svg)
     */
    '/((?!api|v1|ws|_next/static|_next/image|favicon.ico|.*\\.png|.*\\.jpg|.*\\.jpeg|.*\\.svg).*)',
  ],
};
