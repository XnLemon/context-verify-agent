from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.config import settings
from app.schemas.document import ParseResponse
from app.schemas.review import HealthResponse, ReviewRequest, ReviewResponse
from app.services.review_service import ReviewService


router = APIRouter()
review_service = ReviewService()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return review_service.health()


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
