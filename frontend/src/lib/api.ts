import type {
  AuditIssueStatus,
  ChatResponse,
  ClauseRequest,
  ClauseResponse,
  Contract,
  ContractDetailResponse,
  ContractListResponse,
  ContractStatus,
  CreateEmployeeRequest,
  EmployeeListResponse,
  FinalizeContractResponse,
  HistoryItem,
  ImportContractResponse,
  LoginChallengeResponse,
  LoginResponse,
  RedraftResponse,
  ScanResponse,
  SummaryStats,
  TemplateRequest,
  TemplateResponse,
  TemplateTag,
  UpdateProfileRequest,
  UpdateSettingsRequest,
  UserMember,
  AvatarUploadResponse,
} from '@/src/types';
import { getAuthToken } from '@/src/lib/auth';

const viteEnv = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env;
export const API_BASE_URL = viteEnv?.VITE_API_BASE_URL ?? 'http://127.0.0.1:8080';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const token = getAuthToken();
  const authHeader = token ? { Authorization: `Bearer ${token}` } : {};
  const mergedHeaders = isFormData
    ? {
        ...authHeader,
        ...(init?.headers ?? {}),
      }
    : {
        'Content-Type': 'application/json',
        ...authHeader,
        ...(init?.headers ?? {}),
      };

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: mergedHeaders,
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const payload = await response.json();
      detail = payload.detail ?? detail;
    } catch {
      // Ignore JSON parse failures and fall back to status text.
    }
    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

async function sha256Hex(input: string): Promise<string> {
  if (!globalThis.crypto?.subtle) {
    throw new Error('当前浏览器不支持安全登录所需的 WebCrypto。');
  }
  const data = new TextEncoder().encode(input);
  const digest = await globalThis.crypto.subtle.digest('SHA-256', data);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('');
}

export async function login(username: string, password: string) {
  const challenge = await request<LoginChallengeResponse>('/api/auth/login/challenge', {
    method: 'POST',
    body: JSON.stringify({ username }),
  });

  const passwordHash = await sha256Hex(`${challenge.salt}:${password}`);
  const passwordProof = await sha256Hex(`${challenge.nonce}:${passwordHash}`);

  return request<LoginResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({
      username,
      challengeToken: challenge.challengeToken,
      passwordProof,
    }),
  });
}


export function logout() {
  return request<{ message: string }>('/api/auth/logout', {
    method: 'POST',
  });
}
export function getCurrentMember() {
  return request<UserMember>('/api/auth/me');
}

export function getAuthProfile() {
  return request<UserMember>('/api/auth/profile');
}

export function updateAuthProfile(payload: UpdateProfileRequest) {
  return request<UserMember>('/api/auth/profile', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function uploadAuthProfileAvatar(file: File) {
  const formData = new FormData();
  formData.set('file', file);
  return request<AvatarUploadResponse>('/api/auth/profile/avatar', {
    method: 'POST',
    body: formData,
    headers: {},
  });
}

export function getAuthSettings() {
  return request<UserMember>('/api/auth/settings');
}

export function updateAuthSettings(payload: UpdateSettingsRequest) {
  return request<UserMember>('/api/auth/settings', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function buildApiAssetUrl(path: string | null | undefined): string | null {
  if (!path) {
    return null;
  }
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  if (path.startsWith('/')) {
    return `${API_BASE_URL}${path}`;
  }
  return `${API_BASE_URL}/${path}`;
}

export function getEmployees() {
  return request<EmployeeListResponse>('/api/admin/employees');
}

export function createEmployee(payload: CreateEmployeeRequest) {
  return request<UserMember>('/api/admin/employees', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getWorkbenchSummary() {
  return request<SummaryStats>('/api/workbench/summary');
}

export function getWorkbenchContracts(
  paramsOrSearch?:
    | string
    | {
        search?: string;
        status?: ContractStatus;
      },
) {
  const normalized =
    typeof paramsOrSearch === 'string'
      ? { search: paramsOrSearch }
      : (paramsOrSearch ?? {});
  const params = new URLSearchParams();
  if (normalized.search?.trim()) {
    params.set('search', normalized.search.trim());
  }
  if (normalized.status) {
    params.set('status', normalized.status);
  }
  const query = params.toString();
  return request<ContractListResponse>(`/api/workbench/contracts${query ? `?${query}` : ''}`);
}

export function getWorkbenchContractDetail(contractId: string) {
  return request<ContractDetailResponse>(`/api/workbench/contracts/${contractId}`);
}

export function updateWorkbenchContractContent(contractId: string, content: string) {
  return request<Contract>(`/api/workbench/contracts/${contractId}`, {
    method: 'PATCH',
    body: JSON.stringify({ content }),
  });
}

export function finalizeWorkbenchContract(
  contractId: string,
  status: Extract<ContractStatus, 'approved' | 'rejected'>,
  comment?: string,
) {
  return request<FinalizeContractResponse>(`/api/workbench/contracts/${contractId}/final-decision`, {
    method: 'POST',
    body: JSON.stringify({ status, comment }),
  });
}

export function scanWorkbenchContract(contractId: string, ourSide = '甲方') {
  const formData = new FormData();
  formData.set('our_side', ourSide);
  return request<ScanResponse>(`/api/workbench/contracts/${contractId}/scan`, {
    method: 'POST',
    body: formData,
    headers: {},
  });
}

export function sendWorkbenchChatMessage(contractId: string, message: string) {
  return request<ChatResponse>(`/api/workbench/contracts/${contractId}/chat`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  });
}

type ChatStreamStartEvent = {
  id: string;
  timestamp: string;
};

type ChatStreamDeltaEvent = {
  delta: string;
};

type ChatStreamErrorEvent = {
  error: string;
};

type ChatStreamReasoningEvent = {
  step: number;
  summary: string;
};

type ChatStreamActionEvent = {
  step: number;
  name: string;
  input_preview?: string;
};

type ChatStreamObservationEvent = {
  step: number;
  action: string;
  success: boolean;
  summary: string;
  refs?: string[];
};

export async function sendWorkbenchChatMessageStream(
  contractId: string,
  message: string,
  handlers?: {
    onStart?: (event: ChatStreamStartEvent) => void;
    onDelta?: (event: ChatStreamDeltaEvent) => void;
    onReasoning?: (event: ChatStreamReasoningEvent) => void;
    onAction?: (event: ChatStreamActionEvent) => void;
    onObservation?: (event: ChatStreamObservationEvent) => void;
  },
) {
  const token = getAuthToken();
  const authHeader = token ? { Authorization: `Bearer ${token}` } : {};
  const response = await fetch(`${API_BASE_URL}/api/workbench/contracts/${contractId}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeader,
    },
    body: JSON.stringify({ message }),
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const payload = await response.json();
      detail = payload.detail ?? detail;
    } catch {
      // Ignore JSON parse failures and fall back to status text.
    }
    throw new Error(detail);
  }

  if (!response.body) {
    throw new Error('当前浏览器不支持流式响应。');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let finalPayload: ChatResponse | null = null;

  const findBoundary = (value: string) => {
    const lf = value.indexOf('\n\n');
    const crlf = value.indexOf('\r\n\r\n');
    if (lf === -1) {
      return { index: crlf, length: crlf === -1 ? 0 : 4 };
    }
    if (crlf === -1) {
      return { index: lf, length: 2 };
    }
    return lf < crlf ? { index: lf, length: 2 } : { index: crlf, length: 4 };
  };

  const processBlock = (block: string) => {
    const lines = block
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean);
    if (lines.length === 0) {
      return;
    }

    let event = 'message';
    const dataLines: string[] = [];

    for (const line of lines) {
      if (line.startsWith('event:')) {
        event = line.slice(6).trim();
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trim());
      }
    }

    if (dataLines.length === 0) {
      return;
    }

    const raw = dataLines.join('\n');

    if (event === 'start') {
      handlers?.onStart?.(JSON.parse(raw) as ChatStreamStartEvent);
      return;
    }

    if (event === 'delta') {
      handlers?.onDelta?.(JSON.parse(raw) as ChatStreamDeltaEvent);
      return;
    }

    if (event === 'done') {
      finalPayload = JSON.parse(raw) as ChatResponse;
      return;
    }

    if (event === 'reasoning') {
      handlers?.onReasoning?.(JSON.parse(raw) as ChatStreamReasoningEvent);
      return;
    }

    if (event === 'action') {
      handlers?.onAction?.(JSON.parse(raw) as ChatStreamActionEvent);
      return;
    }

    if (event === 'observation') {
      handlers?.onObservation?.(JSON.parse(raw) as ChatStreamObservationEvent);
      return;
    }

    if (event === 'error') {
      const errorPayload = JSON.parse(raw) as ChatStreamErrorEvent;
      throw new Error(errorPayload.error || '流式聊天失败。');
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      buffer += decoder.decode();
      break;
    }
    buffer += decoder.decode(value, { stream: true });

    let boundary = findBoundary(buffer);
    while (boundary.index !== -1) {
      const block = buffer.slice(0, boundary.index);
      processBlock(block);
      buffer = buffer.slice(boundary.index + boundary.length);
      boundary = findBoundary(buffer);
    }
  }

  const tail = buffer.trim();
  if (tail) {
    processBlock(tail);
  }

  if (!finalPayload) {
    throw new Error('流式响应未返回完整结果。');
  }

  return finalPayload;
}

export function updateWorkbenchIssueStatus(
  contractId: string,
  issueId: string,
  status: AuditIssueStatus,
  autoRedraft = true,
) {
  return request<ScanResponse['latestReview']>(
    `/api/workbench/contracts/${contractId}/issues/${issueId}/decision`,
    {
      method: 'POST',
      body: JSON.stringify({ status, auto_redraft: autoRedraft }),
    },
  );
}

export function getWorkbenchHistory(contractId: string) {
  return request<HistoryItem[]>(`/api/workbench/contracts/${contractId}/history`);
}

export function redraftWorkbenchContract(contractId: string, ourSide = '甲方') {
  return request<RedraftResponse>(`/api/workbench/contracts/${contractId}/redraft`, {
    method: 'POST',
    body: JSON.stringify({ our_side: ourSide }),
  });
}

export function importWorkbenchContract(
  file: File,
  options?: {
    author?: string;
    contractType?: string;
  },
) {
  const formData = new FormData();
  formData.set('file', file);
  if (options?.author) {
    formData.set('author', options.author);
  }
  if (options?.contractType?.trim()) {
    formData.set('contract_type', options.contractType.trim());
  }

  return request<ImportContractResponse>('/api/workbench/contracts/import', {
    method: 'POST',
    body: formData,
    headers: {},
  });
}

// === Template Tags ===
export function listTags(): Promise<TemplateTag[]> {
  return request<TemplateTag[]>('/api/tags');
}

export function createTag(name: string, color: string): Promise<TemplateTag> {
  return request<TemplateTag>('/api/tags', {
    method: 'POST',
    body: JSON.stringify({ name, color }),
  });
}

export function updateTag(id: number, name: string, color: string): Promise<TemplateTag> {
  return request<TemplateTag>(`/api/tags/${id}`, {
    method: 'PUT',
    body: JSON.stringify({ name, color }),
  });
}

export function deleteTag(id: number): Promise<void> {
  return request<void>(`/api/tags/${id}`, { method: 'DELETE' });
}

// === Templates ===
export function listTemplates(params?: { search?: string; tagIds?: number[]; page?: number; size?: number }): Promise<TemplateResponse[]> {
  const q = new URLSearchParams();
  if (params?.search) q.set('search', params.search);
  if (params?.tagIds?.length) q.set('tagIds', params.tagIds.join(','));
  if (params?.page) q.set('page', String(params.page));
  if (params?.size) q.set('size', String(params.size));
  return request<TemplateResponse[]>(`/api/templates?${q}`);
}

export function getTemplate(id: string): Promise<TemplateResponse> {
  return request<TemplateResponse>(`/api/templates/${id}`);
}

export function createTemplate(data: TemplateRequest): Promise<TemplateResponse> {
  return request<TemplateResponse>('/api/templates', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function updateTemplate(id: string, data: TemplateRequest): Promise<TemplateResponse> {
  return request<TemplateResponse>(`/api/templates/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export function deleteTemplate(id: string): Promise<void> {
  return request<void>(`/api/templates/${id}`, { method: 'DELETE' });
}

// === Clauses ===
export function listClauses(params?: { search?: string; tagIds?: number[]; page?: number; size?: number }): Promise<ClauseResponse[]> {
  const q = new URLSearchParams();
  if (params?.search) q.set('search', params.search);
  if (params?.tagIds?.length) q.set('tagIds', params.tagIds.join(','));
  if (params?.page) q.set('page', String(params.page));
  if (params?.size) q.set('size', String(params.size));
  return request<ClauseResponse[]>(`/api/clauses?${q}`);
}

export function getClause(id: string): Promise<ClauseResponse> {
  return request<ClauseResponse>(`/api/clauses/${id}`);
}

export function createClause(data: ClauseRequest): Promise<ClauseResponse> {
  return request<ClauseResponse>('/api/clauses', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function updateClause(id: string, data: ClauseRequest): Promise<ClauseResponse> {
  return request<ClauseResponse>(`/api/clauses/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export function deleteClause(id: string): Promise<void> {
  return request<void>(`/api/clauses/${id}`, { method: 'DELETE' });
}
