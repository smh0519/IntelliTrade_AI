import { NextResponse } from "next/server";
import * as fs from "fs";
import * as path from "path";

const DATA_FILE = path.join(process.cwd(), "..", "backend", "data", "withdrawal_reservation.json");

function loadReservation(): { amount: number | null } {
  try {
    const raw = fs.readFileSync(DATA_FILE, "utf-8");
    return JSON.parse(raw);
  } catch {
    return { amount: null };
  }
}

function saveReservation(amount: number | null) {
  const dir = path.dirname(DATA_FILE);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(DATA_FILE, JSON.stringify({ amount }, null, 4), "utf-8");
}

// 예약 조회
export async function GET() {
  return NextResponse.json(loadReservation());
}

// 예약 설정
export async function POST(req: Request) {
  try {
    const body = await req.json();
    let amount: number | null = null;

    if (typeof body.amount === "number" && body.amount > 0) {
      amount = body.amount;
    } else if (typeof body.percentage === "number" && body.percentage > 0 && body.percentage <= 100) {
      // 총 자산 대비 % 계산은 클라이언트에서 변환 후 amount로 전달
      amount = body.amount;
    }

    if (amount === null || amount <= 0) {
      return NextResponse.json({ error: "유효한 금액을 입력하세요." }, { status: 400 });
    }

    saveReservation(amount);
    return NextResponse.json({ amount });
  } catch {
    return NextResponse.json({ error: "요청 처리 실패" }, { status: 500 });
  }
}

// 예약 취소
export async function DELETE() {
  saveReservation(null);
  return NextResponse.json({ amount: null });
}
