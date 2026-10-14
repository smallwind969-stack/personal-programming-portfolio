import type { ExperimentTextFileUploadRequest } from "@/lib/schemas";

const binaryExtensions = /\.(xlsx|xls|raw|dat|bin)$/i;

export async function buildExperimentFilePayload(file: File, sourceAssetId?: string, sourceConversionNote?: string): Promise<ExperimentTextFileUploadRequest> {
  const source = sourceAssetId ? { sourceAssetId, sourceConversionNote: sourceConversionNote?.trim() || null } : {};
  if (!binaryExtensions.test(file.name)) return { fileName: file.name, content: await file.text(), encoding: "utf8", ...source };
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 0x8000) binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
  return { fileName: file.name, content: btoa(binary), encoding: "base64", ...source };
}

export const experimentFileAccept = ".csv,.txt,.tsv,.xlsx,.xls,.raw,.dat,.bin,text/csv,text/plain";

export function experimentParseStatusLabel(status: string): string {
  if (status === "parsed") return "已解析";
  if (status === "awaiting_adapter") return "已保存原件，等待设备适配";
  return "解析失败，等待人工处理";
}
