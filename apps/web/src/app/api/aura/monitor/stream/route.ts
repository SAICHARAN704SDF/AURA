export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// Next's general-purpose rewrite proxy can buffer an event stream. Forward
// the iterable response body directly so each backend span reaches EventSource.
export async function GET(request: Request) {
  const from = new URL(request.url);
  const to = new URL(
    "/monitor/stream",
    process.env.AURA_API_ORIGIN || "http://127.0.0.1:8000",
  );
  to.search = from.search;
  const cursor = request.headers.get("last-event-id");
  try {
    const upstream = await fetch(to, {
      cache: "no-store",
      signal: request.signal,
      headers: {
        Accept: "text/event-stream",
        ...(cursor ? { "Last-Event-ID": cursor } : {}),
      },
    });
    return new Response(upstream.body, {
      status: upstream.status,
      headers: {
        "Content-Type":
          upstream.headers.get("content-type") || "text/event-stream",
        "Cache-Control": "no-store, no-transform",
        "X-Accel-Buffering": "no",
        "Content-Encoding": "identity",
      },
    });
  } catch {
    return Response.json(
      { error: "event_stream_unavailable" },
      { status: 503 },
    );
  }
}
