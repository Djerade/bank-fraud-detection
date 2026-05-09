import { NextResponse } from "next/server";

import { getKafkaDashboardSnapshot, isKafkaConfigured, startKafkaConsumerBackground } from "@/lib/kafka-buffer";
import { getDashboardSnapshot } from "@/lib/mock-stream";

export const revalidate = 0;
export const dynamic = "force-dynamic";

export async function GET() {
  if (isKafkaConfigured()) {
    startKafkaConsumerBackground();
    return NextResponse.json(getKafkaDashboardSnapshot());
  }
  return NextResponse.json(getDashboardSnapshot());
}
