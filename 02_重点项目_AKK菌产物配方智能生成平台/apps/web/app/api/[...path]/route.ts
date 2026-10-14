import { NextRequest, NextResponse } from "next/server";

const apiBaseUrl = process.env.SERVER_API_BASE_URL ?? "http://127.0.0.1:8000";
let managedAccessToken: string | null = null;

async function getManagedAccessToken() {
  if (managedAccessToken) return managedAccessToken;
  const response = await fetch(`${apiBaseUrl}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username: process.env.BOOTSTRAP_ADMIN_USERNAME ?? "admin",
      password: process.env.BOOTSTRAP_ADMIN_PASSWORD ?? "JZQY-Admin-2026!",
    }),
    cache: "no-store",
  });
  if (!response.ok) throw new Error("Managed administrator login failed");
  const session = (await response.json()) as { accessToken: string };
  managedAccessToken = session.accessToken;
  return managedAccessToken;
}

type RouteContext = {
  params: Promise<{
    path: string[];
  }>;
};

async function proxyRequest(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  const upstreamUrl = new URL(`/${path.join("/")}`, apiBaseUrl);
  upstreamUrl.search = request.nextUrl.search;

  const body = request.method === "GET" || request.method === "HEAD" ? undefined : await request.text();
  const send = (token: string) =>
    fetch(upstreamUrl, {
      method: request.method,
      headers: {
        "Content-Type": request.headers.get("content-type") ?? "application/json",
        Authorization: `Bearer ${token}`,
      },
      body,
      cache: "no-store",
    });

  let response = await send(await getManagedAccessToken());
  if (response.status === 401) {
    managedAccessToken = null;
    response = await send(await getManagedAccessToken());
  }

  const text = await response.text();
  return new NextResponse(text, {
    status: response.status,
    headers: {
      "Content-Type": response.headers.get("content-type") ?? "application/json",
    },
  });
}

export async function GET(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export async function POST(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}
