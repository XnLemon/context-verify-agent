from __future__ import annotations

import json
import os
from concurrent import futures

import grpc

from app.core.config import settings
from app.schemas.chat import ChatRequest
from app.schemas.review import ReviewRequest
from app.services.chat_service import ChatService
from app.services.review_service import ReviewService
from app.llm.editor import ContractEditor

try:
    from app.agent_rpc import agent_pb2, agent_pb2_grpc
except Exception as exc:  # pragma: no cover
    raise RuntimeError("Missing gRPC generated files. Run: ./app/agent_rpc/gen_proto.sh") from exc


class AgentRpcServicer(agent_pb2_grpc.AgentRpcServiceServicer):
    def __init__(self) -> None:
        self.review_service = ReviewService()
        self.chat_service = ChatService()
        self.contract_editor: ContractEditor | None = None

    def Health(self, request, context):
        health = self.review_service.health()
        return agent_pb2.HealthResponse(
            status=health.status,
            llm_configured=health.llm_configured,
            knowledge_base_ready=health.knowledge_base_ready,
            version="agent-python-1.0",
            capabilities=["health", "parse", "review", "chat", "redraft"],
        )

    def ParseFile(self, request, context):
        try:
            doc = self.review_service.parse_file(request.file_name, request.content)
            payload = {"document": doc.model_dump(mode="json")}
            return agent_pb2.JsonResponse(code=200, json=json.dumps(payload, ensure_ascii=False))
        except ValueError as exc:
            return agent_pb2.JsonResponse(code=400, error=str(exc))
        except RuntimeError as exc:
            return agent_pb2.JsonResponse(code=503, error=str(exc))

    def Review(self, request, context):
        try:
            if request.HasField("contract_text"):
                result = self.review_service.review(
                    ReviewRequest(
                        contract_text=request.contract_text,
                        contract_type=request.contract_type or None,
                        our_side=request.our_side or "甲方",
                    )
                )
            else:
                result = self.review_service.review_file(
                    file_name=request.file.file_name,
                    content=request.file.content,
                    contract_type=request.contract_type or None,
                    our_side=request.our_side or "甲方",
                )
            return agent_pb2.JsonResponse(code=200, json=result.model_dump_json())
        except ValueError as exc:
            return agent_pb2.JsonResponse(code=400, error=str(exc))
        except RuntimeError as exc:
            return agent_pb2.JsonResponse(code=503, error=str(exc))

    def Chat(self, request, context):
        try:
            payload = json.loads(request.payload_json)
            chat_request = ChatRequest.model_validate(payload)
            result = self.chat_service.chat(chat_request)
            return agent_pb2.JsonResponse(code=200, json=result.model_dump_json())
        except ValueError as exc:
            return agent_pb2.JsonResponse(code=400, error=str(exc))
        except RuntimeError as exc:
            return agent_pb2.JsonResponse(code=503, error=str(exc))

    def Redraft(self, request, context):
        try:
            accepted_issues = json.loads(request.accepted_issues_json)
            if not settings.qwen_api_key:
                raise RuntimeError("QWEN_API_KEY 未配置，无法生成合同修订稿。")
            if self.contract_editor is None:
                self.contract_editor = ContractEditor()
            editor = self.contract_editor
            revised = editor.redraft_contract(
                contract_text=request.contract_text,
                contract_type=request.contract_type,
                our_side=request.our_side,
                accepted_issues=accepted_issues,
            )
            return agent_pb2.JsonResponse(code=200, json=json.dumps({"revised_text": revised}, ensure_ascii=False))
        except ValueError as exc:
            return agent_pb2.JsonResponse(code=400, error=str(exc))
        except RuntimeError as exc:
            return agent_pb2.JsonResponse(code=503, error=str(exc))


def serve() -> None:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=16))
    agent_pb2_grpc.add_AgentRpcServiceServicer_to_server(AgentRpcServicer(), server)
    port = int(os.getenv("AGENT_GRPC_PORT", "50051"))
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
