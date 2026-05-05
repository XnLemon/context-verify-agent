export type ContractStatus = 'pending' | 'reviewing' | 'approved' | 'rejected';
export type AuditIssueType = 'risk' | 'suggestion' | 'compliance';
export type AuditIssueSeverity = 'high' | 'medium' | 'low' | 'info';
export type AuditIssueStatus = 'pending' | 'accepted' | 'rejected';
export type MemberType = 'legal' | 'procurement' | 'business';
export type ThemePreference = 'light' | 'dark' | 'system';
export type FontScale = 'small' | 'medium' | 'large';

export interface Contract {
  id: string;
  title: string;
  type: string;
  status: ContractStatus;
  updatedAt: string;
  author: string;
  content: string;
}

export interface SummaryStats {
  pendingCount: number;
  complianceRate: number;
  highRiskCount: number;
  averageReviewDurationHours: number;
  totalContracts: number;
}

export interface AuditIssue {
  id: string;
  type: AuditIssueType;
  severity: AuditIssueSeverity;
  message: string;
  suggestion: string;
  location?: string;
  status?: AuditIssueStatus;
  startIndex?: number;
  endIndex?: number;
}

export interface ReviewSummary {
  contract_type: string;
  overall_risk: AuditIssueSeverity;
  risk_count: number;
}

export interface ReviewResult {
  summary: ReviewSummary;
  reportOverview: string;
  keyFindings: string[];
  nextActions: string[];
  issues: AuditIssue[];
  generatedAt: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  traceSummary?: ChatTraceSummaryItem[];
}

export interface HistoryItem {
  id: string;
  type: 'scan' | 'issue_decision' | 'chat' | 'import' | 'redraft' | 'manual_edit' | 'final_decision';
  title: string;
  description: string;
  createdAt: string;
  metadata: Record<string, string>;
}

export interface ContractListResponse {
  items: Contract[];
  total: number;
}

export interface ContractDetailResponse {
  contract: Contract;
  latestReview: ReviewResult | null;
  chatMessages: ChatMessage[];
}

export interface ScanResponse {
  contract: Contract;
  latestReview: ReviewResult;
  historyCount: number;
}

export interface ChatResponse {
  intent: string;
  toolUsed: string;
  assistantMessage: ChatMessage;
  messages: ChatMessage[];
  latestReview: ReviewResult | null;
  traceSummary?: ChatTraceSummaryItem[];
}

export interface ChatTraceSummaryItem {
  step: number;
  thought?: string;
  action?: string;
  observation?: string;
}

export interface ImportContractResponse {
  contract: Contract;
}

export interface RedraftResponse {
  contract: Contract;
  latestReview: ReviewResult;
  acceptedIssueCount: number;
}

export interface FinalizeContractResponse {
  contract: Contract;
  historyCount: number;
}

export type UserRole = 'admin' | 'employee';
export type UserMemberType = 'admin' | 'legal' | 'procurement' | 'business' | 'other';

export interface UserMember {
  id: number;
  username: string;
  displayName: string;
  role: UserRole;
  memberType: UserMemberType;
  isActive: boolean;
  avatarUrl: string | null;
  themePreference: ThemePreference;
  fontScale: FontScale;
  notifyEnabled: boolean;
  lastLoginAt: string | null;
  createdAt: string;
}

export interface LoginChallengeResponse {
  challengeToken: string;
  nonce: string;
  salt: string;
  expiresAt: string;
}

export interface LoginResponse {
  token: string;
  expiresAt: string;
  member: UserMember;
}

export interface EmployeeListResponse {
  items: UserMember[];
  total: number;
}

export interface CreateEmployeeRequest {
  username: string;
  password: string;
  displayName: string;
  memberType: Exclude<UserMemberType, 'admin'>;
}


export interface UpdateProfileRequest {
  displayName: string;
}

export interface UpdateSettingsRequest {
  themePreference: ThemePreference;
  fontScale: FontScale;
  notifyEnabled: boolean;
}

export interface AvatarUploadResponse {
  avatarUrl: string;
  member: UserMember;
}

export interface TemplateTag {
  id: number;
  name: string;
  color: string;
}

export interface TemplateRequest {
  name: string;
  description?: string;
  content: string;
  tags: number[];
}

export interface TemplateResponse {
  id: string;
  name: string;
  description?: string;
  content: string;
  tags: TemplateTag[];
  createdBy: string;
  updatedBy: string;
  createdAt: string;
  updatedAt: string;
}

export interface ClauseRequest {
  title: string;
  content: string;
  tags: number[];
}

export interface ClauseResponse {
  id: string;
  title: string;
  content: string;
  tags: TemplateTag[];
  createdBy: string;
  updatedBy: string;
  createdAt: string;
  updatedAt: string;
}
