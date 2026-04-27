package com.example.contract.controller;

import com.example.contract.dto.*;
import com.example.contract.exception.ApiException;
import com.example.contract.model.Member;
import com.example.contract.service.auth.AuthorizationService;
import com.example.contract.service.workbench.WorkbenchService;
import com.example.contract.util.Jsons;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;
import java.util.Map;

@RestController
public class WorkbenchController {
    private final WorkbenchService workbenchService;
    private final AuthorizationService authorizationService;

    public WorkbenchController(WorkbenchService workbenchService, AuthorizationService authorizationService) {
        this.workbenchService = workbenchService;
        this.authorizationService = authorizationService;
    }

    @GetMapping("/api/workbench/summary")
    public SummaryResponse summary(@RequestHeader(value = "authorization", required = false) String authorization) {
        Member member = authorizationService.requireLoggedIn(authorization);
        return workbenchService.summary(member);
    }

    @GetMapping("/api/workbench/contracts")
    public ContractListResponse contracts(@RequestHeader(value = "authorization", required = false) String authorization,
                                         @RequestParam(value = "status", required = false) String status,
                                         @RequestParam(value = "search", required = false) String search) {
        Member member = authorizationService.requireLoggedIn(authorization);
        return workbenchService.listContracts(status, search, member);
    }

    @GetMapping("/api/workbench/contracts/{contractId}")
    public ContractDetailResponse detail(@RequestHeader(value = "authorization", required = false) String authorization,
                                      @PathVariable String contractId) {
        Member member = authorizationService.requireLoggedIn(authorization);
        return workbenchService.contractDetail(contractId, member);
    }

    @PatchMapping("/api/workbench/contracts/{contractId}")
    public ContractResponse update(@RequestHeader(value = "authorization", required = false) String authorization,
                                      @PathVariable String contractId,
                                      @RequestBody Map<String, Object> payload) {
        Member member = authorizationService.requireEmployeeOperator(authorization);
        return workbenchService.updateContractContent(contractId, String.valueOf(payload.getOrDefault("content", "")), member);
    }

    @PostMapping(
            value = "/api/workbench/contracts/{contractId}/scan",
            consumes = {MediaType.APPLICATION_FORM_URLENCODED_VALUE, MediaType.MULTIPART_FORM_DATA_VALUE}
    )
    public ScanResponse scan(@RequestHeader(value = "authorization", required = false) String authorization,
                                    @PathVariable String contractId,
                                    @RequestParam(value = "contract_type", required = false) String contractType,
                                    @RequestParam(value = "our_side", defaultValue = "甲方") String ourSide) {
        Member member = authorizationService.requireLoggedIn(authorization);
        return workbenchService.scanContract(contractId, contractType, ourSide, member);
    }

    @PostMapping("/api/workbench/contracts/{contractId}/chat")
    public ChatResponse chat(@RequestHeader(value = "authorization", required = false) String authorization,
                                    @PathVariable String contractId,
                                    @RequestBody Map<String, Object> payload) {
        Member member = authorizationService.requireLoggedIn(authorization);
        return workbenchService.chatContract(contractId, payload, member);
    }

    @PostMapping(value = "/api/workbench/contracts/{contractId}/chat/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter chatStream(@RequestHeader(value = "authorization", required = false) String authorization,
                                 @PathVariable String contractId,
                                 @RequestBody Map<String, Object> payload) {
        Member member = authorizationService.requireLoggedIn(authorization);
        SseEmitter emitter = new SseEmitter(0L);

        Thread.startVirtualThread(() -> {
            try {
                workbenchService.chatContractStream(contractId, payload, member, event -> {
                    try {
                        emitter.send(SseEmitter.event()
                                .name(event.event())
                                .data(event.dataJson()));
                    } catch (Exception sendEx) {
                        throw new RuntimeException(sendEx);
                    }
                });
                emitter.complete();
            } catch (Exception ex) {
                try {
                    emitter.send(SseEmitter.event()
                            .name("error")
                            .data(Jsons.toJson(Map.of("error", ex.getMessage() == null ? "chat stream failed" : ex.getMessage()))));
                } catch (Exception ignored) {
                    // Ignore secondary stream send failures.
                }
                emitter.completeWithError(ex);
            }
        });

        return emitter;
    }

    @PostMapping("/api/workbench/contracts/{contractId}/issues/{issueId}/decision")
    public ReviewResultResponse decision(@RequestHeader(value = "authorization", required = false) String authorization,
                                        @PathVariable String contractId,
                                        @PathVariable String issueId,
                                        @RequestBody Map<String, Object> payload) {
        Member member = authorizationService.requireLoggedIn(authorization);
        return workbenchService.decideIssue(contractId, issueId, payload, member);
    }

    @PostMapping("/api/workbench/contracts/{contractId}/final-decision")
    public FinalizeResponse finalDecision(@RequestHeader(value = "authorization", required = false) String authorization,
                                             @PathVariable String contractId,
                                             @RequestBody Map<String, Object> payload) {
        Member member = authorizationService.requireFinalApprover(authorization);
        return workbenchService.finalizeContract(contractId, String.valueOf(payload.getOrDefault("status", "")), member.displayName(),
                payload.get("comment") == null ? null : payload.get("comment").toString(), member);
    }

    @PostMapping("/api/workbench/contracts/{contractId}/redraft")
    public RedraftResponse redraft(@RequestHeader(value = "authorization", required = false) String authorization,
                                       @PathVariable String contractId,
                                       @RequestBody Map<String, Object> payload) {
        Member member = authorizationService.requireLoggedIn(authorization);
        return workbenchService.redraftContract(contractId, String.valueOf(payload.getOrDefault("our_side", "甲方")), member);
    }

    @GetMapping("/api/workbench/contracts/{contractId}/history")
    public List<HistoryResponse> history(@RequestHeader(value = "authorization", required = false) String authorization,
                                             @PathVariable String contractId) {
        Member member = authorizationService.requireLoggedIn(authorization);
        return workbenchService.history(contractId, member);
    }

    @PostMapping(value = "/api/workbench/contracts/import", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ImportContractResponse importContract(@RequestHeader(value = "authorization", required = false) String authorization,
                                              @RequestParam("file") MultipartFile file,
                                              @RequestParam(value = "contract_type", required = false) String contractType,
                                              @RequestParam(value = "author", required = false) String author) throws Exception {
        Member member = authorizationService.requireEmployeeOperator(authorization);
        if (file.isEmpty()) {
            throw new ApiException(400, "上传文件不能为空。");
        }
        return workbenchService.importContract(file.getOriginalFilename(), file.getBytes(), contractType,
                author == null || author.isBlank() ? member.displayName() : author, member.username(), member);
    }

}
