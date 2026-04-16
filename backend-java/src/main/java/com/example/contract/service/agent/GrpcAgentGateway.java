package com.example.contract.service.agent;

import com.example.contract.agent.v1.*;
import com.example.contract.exception.ApiException;
import com.example.contract.util.Jsons;
import com.google.protobuf.ByteString;
import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import io.grpc.StatusRuntimeException;

import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

public class GrpcAgentGateway implements AgentGateway {
    private final ManagedChannel channel;
    private final AgentRpcServiceGrpc.AgentRpcServiceBlockingStub stub;
    private final long timeoutMillis;

    public GrpcAgentGateway(String target, long timeoutMillis) {
        this.channel = ManagedChannelBuilder.forTarget(target).usePlaintext().build();
        this.stub = AgentRpcServiceGrpc.newBlockingStub(channel);
        this.timeoutMillis = timeoutMillis;
    }

    @Override
    public Map<String, Object> health() {
        HealthResponse res = call(() -> withTimeout().health(HealthRequest.newBuilder().build()));
        return Map.of(
                "status", res.getStatus(),
                "llm_configured", res.getLlmConfigured(),
                "knowledge_base_ready", res.getKnowledgeBaseReady(),
                "version", res.getVersion(),
                "capabilities", res.getCapabilitiesList()
        );
    }

    @Override
    public Map<String, Object> parseFile(String fileName, byte[] content) {
        ParseFileRequest req = ParseFileRequest.newBuilder().setFileName(fileName).setContent(ByteString.copyFrom(content)).build();
        return parseJson(call(() -> withTimeout().parseFile(req)));
    }

    @Override
    public Map<String, Object> reviewText(String contractText, String contractType, String ourSide) {
        ReviewRequest req = ReviewRequest.newBuilder().setContractText(contractText)
                .setContractType(nullToEmpty(contractType)).setOurSide(nullToEmpty(ourSide)).build();
        return parseJson(call(() -> withTimeout().review(req)));
    }

    @Override
    public Map<String, Object> reviewFile(String fileName, byte[] content, String contractType, String ourSide) {
        ReviewRequest req = ReviewRequest.newBuilder()
                .setFile(FilePayload.newBuilder().setFileName(fileName).setContent(ByteString.copyFrom(content)).build())
                .setContractType(nullToEmpty(contractType)).setOurSide(nullToEmpty(ourSide)).build();
        return parseJson(call(() -> withTimeout().review(req)));
    }

    @Override
    public Map<String, Object> chat(Map<String, Object> payload) {
        JsonResponse res = call(() -> withTimeout().chat(ChatRequest.newBuilder().setPayloadJson(Jsons.toJson(payload)).build()));
        return parseJson(res);
    }

    @Override
    public String redraft(String contractText, String contractType, String ourSide, List<Map<String, String>> acceptedIssues) {
        JsonResponse res = call(() -> withTimeout().redraft(RedraftRequest.newBuilder()
                .setContractText(contractText)
                .setContractType(nullToEmpty(contractType))
                .setOurSide(nullToEmpty(ourSide))
                .setAcceptedIssuesJson(Jsons.toJson(acceptedIssues)).build()));
        Map<String, Object> json = parseJson(res);
        Object revised = json.get("revised_text");
        return revised == null ? contractText : revised.toString();
    }

    private JsonResponse call(RpcCall call) {
        try {
            return call.exec();
        } catch (StatusRuntimeException ex) {
            throw new ApiException(503, "Agent RPC 调用失败: " + ex.getStatus().getDescription());
        }
    }

    private HealthResponse call(HealthCall call) {
        try {
            return call.exec();
        } catch (StatusRuntimeException ex) {
            throw new ApiException(503, "Agent RPC 调用失败: " + ex.getStatus().getDescription());
        }
    }

    private Map<String, Object> parseJson(JsonResponse res) {
        if (res.getCode() >= 400) {
            throw new ApiException(res.getCode(), res.getError().isBlank() ? "agent error" : res.getError());
        }
        return Jsons.toMap(res.getJson());
    }

    private String nullToEmpty(String value) {
        return value == null ? "" : value;
    }

    private AgentRpcServiceGrpc.AgentRpcServiceBlockingStub withTimeout() {
        return stub.withDeadlineAfter(timeoutMillis, TimeUnit.MILLISECONDS);
    }

    @FunctionalInterface
    interface RpcCall {
        JsonResponse exec();
    }

    @FunctionalInterface
    interface HealthCall {
        HealthResponse exec();
    }
}
