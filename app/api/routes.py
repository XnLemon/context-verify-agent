from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Request, UploadFile

from app.core.config import settings
from app.schemas.auth import (
    AvatarUploadResponse,
    CreateEmployeeRequest,
    EmployeeListResponse,
    LoginChallengeRequest,
    LoginChallengeResponse,
    LoginRequest,
    LoginResponse,
    MemberPublic,
    ProfileUpdateRequest,
    SettingsUpdateRequest,
)
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.document import ParseResponse
from app.schemas.review import HealthResponse, ReviewRequest, ReviewResponse
from app.schemas.workbench import (
    WorkbenchChatRequest,
    WorkbenchChatResponse,
    WorkbenchContractDetailResponse,
    WorkbenchContractListResponse,
    WorkbenchContractUpdateRequest,
    WorkbenchContractUpdateResponse,
    WorkbenchFinalDecisionRequest,
    WorkbenchFinalDecisionResponse,
    WorkbenchHistoryItem,
    WorkbenchImportResponse,
    WorkbenchIssueDecisionRequest,
    WorkbenchRedraftRequest,
    WorkbenchRedraftResponse,
    WorkbenchReviewResult,
    WorkbenchScanResponse,
    WorkbenchSummaryResponse,
)
from app.services.auth_service import AuthService
from app.services.chat_service import ChatService
from app.services.review_service import ReviewService
from app.services.workbench_service import WorkbenchService


router = APIRouter()
review_service = ReviewService()
chat_service = ChatService()
workbench_service = WorkbenchService()
auth_service = AuthService()

repo_root = Path(__file__).resolve().parents[2]
uploads_root = repo_root / "uploads"
avatar_root = uploads_root / "avatars"
avatar_root.mkdir(parents=True, exist_ok=True)


def _save_avatar_file(member_id: int, file_name: str, content: bytes) -> str:
    extension = Path(file_name).suffix.lower()
    if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise ValueError("头像仅支持 jpg/jpeg/png/webp 格式。")
    if not content:
        raise ValueError("头像文件不能为空。")
    if len(content) > settings.max_avatar_upload_size_bytes:
        raise ValueError("头像文件过大，请控制在 2MB 以内。")

    member_dir = avatar_root / str(member_id)
    member_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    file_path = member_dir / f"avatar-{timestamp}-{uuid4().hex[:8]}{extension}"
    file_path.write_bytes(content)

    relative_path = file_path.relative_to(repo_root).as_posix()
    return f"/{relative_path}"


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return review_service.health()


@router.post("/api/auth/login/challenge", response_model=LoginChallengeResponse)
def login_challenge(payload: LoginChallengeRequest) -> LoginChallengeResponse:
    try:
        return auth_service.issue_login_challenge(username=payload.username)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/api/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request) -> LoginResponse:
    try:
        return auth_service.login_with_proof(
            username=payload.username,
            challenge_token=payload.challenge_token,
            password_proof=payload.password_proof,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/api/auth/logout")
def logout(authorization: str | None = Header(default=None)) -> dict[str, str]:
    try:
        auth_service.logout(authorization)
        return {"message": "ok"}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/api/auth/me", response_model=MemberPublic)
def get_current_member(authorization: str | None = Header(default=None)) -> MemberPublic:
    try:
        return auth_service.authenticate_bearer(authorization)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def require_logged_in_member(authorization: str | None = Header(default=None)) -> MemberPublic:
    try:
        return auth_service.authenticate_bearer(authorization)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def require_admin_member(authorization: str | None = Header(default=None)) -> MemberPublic:
    member = require_logged_in_member(authorization)
    if member.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员有权限执行该操作")
    return member


def require_employee_operator_member(authorization: str | None = Header(default=None)) -> MemberPublic:
    member = require_logged_in_member(authorization)
    if member.role != "employee" or member.member_type == "legal":
        raise HTTPException(status_code=403, detail="仅员工可上传或修改合同")
    return member


def require_final_approver_member(authorization: str | None = Header(default=None)) -> MemberPublic:
    member = require_logged_in_member(authorization)
    if member.role == "admin" or member.member_type == "legal":
        return member
    raise HTTPException(status_code=403, detail="仅经理/审核可执行最终审批")


@router.get("/api/auth/profile", response_model=MemberPublic)
def get_profile(member: MemberPublic = Depends(require_logged_in_member)) -> MemberPublic:
    try:
        return auth_service.get_profile(member.id)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.patch("/api/auth/profile", response_model=MemberPublic)
def update_profile(payload: ProfileUpdateRequest, member: MemberPublic = Depends(require_logged_in_member)) -> MemberPublic:
    try:
        return auth_service.update_profile(member.id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/api/auth/profile/avatar", response_model=AvatarUploadResponse)
async def upload_profile_avatar(
    file: UploadFile = File(...),
    member: MemberPublic = Depends(require_logged_in_member),
) -> AvatarUploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="缺少上传文件名。")

    content = await file.read()
    try:
        avatar_url = _save_avatar_file(member.id, file.filename, content)
        updated_member = auth_service.update_avatar(member.id, avatar_url)
        return AvatarUploadResponse(avatar_url=avatar_url, member=updated_member)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/api/auth/settings", response_model=MemberPublic)
def get_settings(member: MemberPublic = Depends(require_logged_in_member)) -> MemberPublic:
    try:
        return auth_service.get_profile(member.id)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.patch("/api/auth/settings", response_model=MemberPublic)
def update_settings(payload: SettingsUpdateRequest, member: MemberPublic = Depends(require_logged_in_member)) -> MemberPublic:
    try:
        return auth_service.update_settings(member.id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/api/admin/employees", response_model=EmployeeListResponse)
def list_employees(_member: MemberPublic = Depends(require_admin_member)) -> EmployeeListResponse:
    items = auth_service.list_employees()
    return EmployeeListResponse(items=items, total=len(items))


@router.post("/api/admin/employees", response_model=MemberPublic)
def create_employee(
    payload: CreateEmployeeRequest,
    _member: MemberPublic = Depends(require_admin_member),
) -> MemberPublic:
    try:
        return auth_service.create_employee(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/workbench/summary", response_model=WorkbenchSummaryResponse)
def get_workbench_summary(member: MemberPublic = Depends(require_logged_in_member)) -> WorkbenchSummaryResponse:
    return workbench_service.get_summary(current_member=member)


@router.get("/api/workbench/contracts", response_model=WorkbenchContractListResponse)
def list_workbench_contracts(
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    member: MemberPublic = Depends(require_logged_in_member),
) -> WorkbenchContractListResponse:
    return workbench_service.list_contracts(status=status, search=search, current_member=member)


@router.get("/api/workbench/contracts/{contract_id}", response_model=WorkbenchContractDetailResponse)
def get_workbench_contract(
    contract_id: str,
    member: MemberPublic = Depends(require_logged_in_member),
) -> WorkbenchContractDetailResponse:
    try:
        return workbench_service.get_contract_detail(contract_id, current_member=member)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/api/workbench/contracts/{contract_id}", response_model=WorkbenchContractUpdateResponse)
def update_workbench_contract(
    contract_id: str,
    payload: WorkbenchContractUpdateRequest,
    member: MemberPublic = Depends(require_employee_operator_member),
) -> WorkbenchContractUpdateResponse:
    try:
        return workbench_service.update_contract_content(
            contract_id=contract_id,
            content=payload.content,
            current_member=member,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/workbench/contracts/{contract_id}/scan", response_model=WorkbenchScanResponse)
def scan_workbench_contract(
    contract_id: str,
    contract_type: str | None = Form(default=None),
    our_side: str = Form(default="甲方"),
    member: MemberPublic = Depends(require_logged_in_member),
) -> WorkbenchScanResponse:
    try:
        return workbench_service.scan_contract(
            contract_id,
            contract_type=contract_type,
            our_side=our_side,
            current_member=member,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/api/workbench/contracts/{contract_id}/chat", response_model=WorkbenchChatResponse)
def chat_workbench_contract(
    contract_id: str,
    payload: WorkbenchChatRequest,
    member: MemberPublic = Depends(require_logged_in_member),
) -> WorkbenchChatResponse:
    try:
        return workbench_service.chat_contract(contract_id, payload, current_member=member)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post(
    "/api/workbench/contracts/{contract_id}/issues/{issue_id}/decision",
    response_model=WorkbenchReviewResult,
)
def decide_workbench_issue(
    contract_id: str,
    issue_id: str,
    payload: WorkbenchIssueDecisionRequest,
    member: MemberPublic = Depends(require_logged_in_member),
) -> WorkbenchReviewResult:
    try:
        return workbench_service.decide_issue(contract_id, issue_id, payload, current_member=member)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/api/workbench/contracts/{contract_id}/final-decision",
    response_model=WorkbenchFinalDecisionResponse,
)
def finalize_workbench_contract(
    contract_id: str,
    payload: WorkbenchFinalDecisionRequest,
    member: MemberPublic = Depends(require_final_approver_member),
) -> WorkbenchFinalDecisionResponse:
    try:
        return workbench_service.finalize_contract(
            contract_id=contract_id,
            status=payload.status,
            operator_name=member.display_name,
            comment=payload.comment,
            current_member=member,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/workbench/contracts/{contract_id}/redraft", response_model=WorkbenchRedraftResponse)
def redraft_workbench_contract(
    contract_id: str,
    payload: WorkbenchRedraftRequest,
    member: MemberPublic = Depends(require_logged_in_member),
) -> WorkbenchRedraftResponse:
    try:
        return workbench_service.redraft_contract(
            contract_id=contract_id,
            our_side=payload.our_side,
            current_member=member,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/api/workbench/contracts/{contract_id}/history", response_model=list[WorkbenchHistoryItem])
def get_workbench_history(
    contract_id: str,
    member: MemberPublic = Depends(require_logged_in_member),
) -> list[WorkbenchHistoryItem]:
    try:
        return workbench_service.get_history(contract_id, current_member=member)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/workbench/contracts/import", response_model=WorkbenchImportResponse)
async def import_workbench_contract(
    file: UploadFile = File(...),
    contract_type: str | None = Form(default=None),
    author: str | None = Form(default=None),
    member: MemberPublic = Depends(require_employee_operator_member),
) -> WorkbenchImportResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="缺少上传文件名。")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件不能为空。")
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(status_code=400, detail="上传文件过大，请控制在 5MB 以内。")

    try:
        return workbench_service.import_contract(
            file_name=file.filename,
            content=content,
            contract_type=contract_type,
            author=author or member.display_name,
            owner_username=member.username,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post(
    "/parse",
    response_model=ParseResponse,
    summary="上传文件并解析",
    description="上传 txt/docx/pdf 合同文件，返回解析后的结构化文档。",
)
async def parse_contract(file: UploadFile = File(...)) -> ParseResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="缺少上传文件名。")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件不能为空。")
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(status_code=400, detail="上传文件过大，请控制在 5MB 以内。")

    try:
        return ParseResponse(document=review_service.parse_file(file.filename, content))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post(
    "/review",
    response_model=ReviewResponse,
    summary="校审合同文本",
    description="提交合同全文文本，返回结构化校审报告。",
)
def review_contract(payload: ReviewRequest) -> ReviewResponse:
    try:
        return review_service.review(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post(
    "/review/file",
    response_model=ReviewResponse,
    summary="上传文件并校审",
    description="上传 txt/docx/pdf 合同文件，返回结构化校审报告。",
)
async def review_contract_file(
    file: UploadFile = File(...),
    contract_type: str | None = Form(default=None),
    our_side: str = Form(default="甲方"),
) -> ReviewResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="缺少上传文件名。")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件不能为空。")
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(status_code=400, detail="上传文件过大，请控制在 5MB 以内。")

    try:
        return review_service.review_file(
            file_name=file.filename,
            content=content,
            contract_type=contract_type,
            our_side=our_side,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="聊天式合同助手",
    description="根据用户意图自动调用搜索、审查、建议或普通对话能力。",
)
def chat(payload: ChatRequest) -> ChatResponse:
    try:
        return chat_service.chat(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


