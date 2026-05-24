import { NextResponse } from "next/server";

const HEADERS = {
  "User-Agent":
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
  Accept: "text/html,application/xhtml+xml,*/*;q=0.9",
  "Accept-Language": "ko-KR,ko;q=0.9",
  Referer: "https://www.naver.com/",
};

function extractNaverBody(html: string): string | null {
  const articleMatch = html.match(/<article[^>]*>([\s\S]*?)<\/article>/i);
  if (!articleMatch) return null;

  const text = articleMatch[1]
    .replace(/<script[\s\S]*?<\/script>/gi, "")
    .replace(/<style[\s\S]*?<\/style>/gi, "")
    .replace(/<figure[\s\S]*?<\/figure>/gi, "")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#[0-9]+;/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  return text.length > 100 ? text : null;
}

function extractBody(html: string): string {
  let text = html
    .replace(/<script[\s\S]*?<\/script>/gi, "")
    .replace(/<style[\s\S]*?<\/style>/gi, "")
    .replace(/<nav[\s\S]*?<\/nav>/gi, "")
    .replace(/<header[\s\S]*?<\/header>/gi, "")
    .replace(/<footer[\s\S]*?<\/footer>/gi, "")
    .replace(/<aside[\s\S]*?<\/aside>/gi, "")
    .replace(/<figure[\s\S]*?<\/figure>/gi, "")
    .replace(/<!--[\s\S]*?-->/g, "");

  const paragraphs: string[] = [];
  for (const m of text.matchAll(/<p[^>]*>([\s\S]*?)<\/p>/gi)) {
    const clean = m[1]
      .replace(/<[^>]+>/g, "")
      .replace(/&nbsp;/g, " ")
      .replace(/&amp;/g, "&")
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">")
      .replace(/&quot;/g, '"')
      .replace(/&#[0-9]+;/g, " ")
      .replace(/\s+/g, " ")
      .trim();
    if (clean.length > 30) paragraphs.push(clean);
  }

  if (paragraphs.length >= 3) return paragraphs.join("\n\n");

  return text
    .replace(/<[^>]+>/g, " ")
    .replace(/&[a-z#0-9]+;/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

async function crawl(url: string): Promise<{ body: string; finalUrl: string }> {
  const res = await fetch(url, {
    headers: HEADERS,
    signal: AbortSignal.timeout(8000),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const html = await res.text();

  const body = url.includes("n.news.naver.com")
    ? (extractNaverBody(html) ?? extractBody(html))
    : extractBody(html);

  return { body, finalUrl: url };
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const url = searchParams.get("url");

  if (!url || url === "#") {
    return NextResponse.json({ body: null, finalUrl: null });
  }

  try {
    const { body, finalUrl } = await crawl(url);
    return NextResponse.json({
      body: body.length > 100 ? body : null,
      finalUrl,
    });
  } catch (e) {
    console.error("[crawl]", (e as Error).message?.slice(0, 80));
    return NextResponse.json({ body: null, finalUrl: null });
  }
}
