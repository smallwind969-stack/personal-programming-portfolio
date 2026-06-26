import {
  AkkProduct,
  FormulaGenerationRequest,
  FormulaResult,
  ExperimentRecord,
  KnowledgeChunk,
  KnowledgeItem,
  LlmStatus,
  akkProductSchema,
  experimentRecordSchema,
  formulaResultSchema,
  knowledgeChunkSchema,
  knowledgeItemSchema,
  llmStatusSchema,
} from "@/lib/schemas";

const serverApiBaseUrl = process.env.SERVER_API_BASE_URL ?? "http://127.0.0.1:8000";
const publicApiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

function getBaseUrl() {
  if (typeof window === "undefined") {
    return serverApiBaseUrl;
  }
  return publicApiBaseUrl;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getBaseUrl()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<T>;
}

export async function getAkkProducts(): Promise<AkkProduct[]> {
  const data = await requestJson<unknown[]>("/akk-products");
  return data.map((item) => akkProductSchema.parse(item));
}

export async function getAkkProduct(productId: string): Promise<AkkProduct> {
  const data = await requestJson<unknown>(`/akk-products/${productId}`);
  return akkProductSchema.parse(data);
}

export async function generateFormula(
  payload: FormulaGenerationRequest,
): Promise<FormulaResult> {
  const data = await requestJson<unknown>("/formula/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return formulaResultSchema.parse(data);
}

export async function getFormulaResult(resultId: string): Promise<FormulaResult> {
  const data = await requestJson<unknown>(`/formula-results/${resultId}`);
  return formulaResultSchema.parse(data);
}

export async function getFormulaResults(): Promise<FormulaResult[]> {
  const data = await requestJson<unknown[]>("/formula-results");
  return data.map((item) => formulaResultSchema.parse(item));
}

export async function getKnowledgeItems(query?: string): Promise<KnowledgeItem[]> {
  const qs = query ? `?query=${encodeURIComponent(query)}` : "";
  const data = await requestJson<unknown[]>(`/knowledge${qs}`);
  return data.map((item) => knowledgeItemSchema.parse(item));
}

export async function getKnowledgeChunks(query?: string): Promise<KnowledgeChunk[]> {
  const qs = query ? `?query=${encodeURIComponent(query)}&limit=8` : "?limit=8";
  const data = await requestJson<unknown[]>(`/knowledge/chunks${qs}`);
  return data.map((item) => knowledgeChunkSchema.parse(item));
}

export async function getLlmStatus(): Promise<LlmStatus> {
  const data = await requestJson<unknown>("/llm/status");
  return llmStatusSchema.parse(data);
}

export async function getExperimentRecords(resultId?: string): Promise<ExperimentRecord[]> {
  const query = resultId ? `?result_id=${encodeURIComponent(resultId)}` : "";
  const data = await requestJson<unknown[]>(`/experiments${query}`);
  return data.map((item) => experimentRecordSchema.parse(item));
}
