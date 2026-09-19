import { createReadStream, existsSync, statSync } from "node:fs";
import path from "node:path";
import { Readable } from "node:stream";
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ leadId: string }> },
) {
  const { leadId } = await params;
  if (!/^\d+$/.test(leadId)) {
    return new NextResponse("Not found", { status: 404 });
  }

  // Layout: qt-gate/{web,qa-gate}; recordings live under the backend.
  const file = path.resolve(
    process.cwd(),
    "..",
    "qa-gate",
    "demo",
    "audio",
    `${leadId}.mp3`,
  );
  const root = path.resolve(process.cwd(), "..", "qa-gate", "demo", "audio");
  if (!file.startsWith(root) || !existsSync(file)) {
    return new NextResponse("No recording", { status: 404 });
  }

  const { size } = statSync(file);
  const headers = {
    "Content-Type": "audio/mpeg",
    "Accept-Ranges": "bytes",
    "Cache-Control": "public, max-age=3600",
  };

  if (request.method === "HEAD") {
    return new NextResponse(null, {
      status: 200,
      headers: { ...headers, "Content-Length": String(size) },
    });
  }

  const range = request.headers.get("range");
  let start = 0;
  let end = size - 1;
  let status = 200;
  if (range) {
    const match = /bytes=(\d*)-(\d*)/.exec(range);
    if (match) {
      if (match[1]) start = Number(match[1]);
      if (match[2]) end = Number(match[2]);
      if (end >= size) end = size - 1;
      if (start > end) start = 0;
      status = 206;
    }
  }

  const stream = Readable.toWeb(
    createReadStream(file, { start, end }),
  ) as ReadableStream;
  return new NextResponse(stream, {
    status,
    headers: {
      ...headers,
      "Content-Length": String(end - start + 1),
      ...(status === 206
        ? { "Content-Range": `bytes ${start}-${end}/${size}` }
        : {}),
    },
  });
}

export function HEAD(
  request: NextRequest,
  ctx: { params: Promise<{ leadId: string }> },
) {
  return GET(request, ctx);
}
