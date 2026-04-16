import type {
  AuditIssueStatus,
  ChatResponse,
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
      challenge_token: challenge.challenge_token,
      password_proof: passwordProof,
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
  return request<{ contract: Contract }>(`/api/workbench/contracts/${contractId}`, {
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


