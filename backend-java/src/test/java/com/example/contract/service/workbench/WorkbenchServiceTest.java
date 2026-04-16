package com.example.contract.service.workbench;

import com.example.contract.config.AppProperties;
import com.example.contract.exception.ApiException;
import com.example.contract.model.Member;
import com.example.contract.repository.WorkbenchRepository;
import com.example.contract.service.agent.AgentGateway;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class WorkbenchServiceTest {
    private WorkbenchRepository repository;
    private AgentGateway agentGateway;
    private WorkbenchService service;
    private Member member;

    @BeforeEach
    void setUp() {
        repository = mock(WorkbenchRepository.class);
        agentGateway = mock(AgentGateway.class);
        service = new WorkbenchService(repository, agentGateway, new AppProperties());
        member = new Member(1, "u1", "User One", "employee", "legal", true,
                null, "system", "medium", true, OffsetDateTime.now(), null);
        when(repository.appendHistory(anyString(), anyInt(), anyMap())).thenReturn(1);
    }

    @Test
    void decideIssueRejectsInvalidStatus() {
        String contractId = "c-1";
        String issueId = "iss-1";
        when(repository.getContract(contractId)).thenReturn(Optional.of(contract(contractId)));
        when(repository.getReview(contractId)).thenReturn(Optional.of(reviewWithIssues(List.of(issue(issueId, "pending")))));

        ApiException ex = assertThrows(ApiException.class,
                () -> service.decideIssue(contractId, issueId, Map.of("status", "approved"), member));
        assertEquals(400, ex.getStatus());
        verify(repository, never()).saveReview(anyString(), anyMap(), anyString(), anyList(), anyList(), anyList(), any());
    }

    @Test
    void decideIssueKeepsReviewingWhenUnknownStatusExists() {
        String contractId = "c-2";
        String issueId = "iss-1";
        Map<String, Object> review = reviewWithIssues(new ArrayList<>(List.of(
                issue(issueId, "pending"),
                issue("iss-2", "mystery")
        )));
        when(repository.getContract(contractId)).thenReturn(Optional.of(contract(contractId)));
        when(repository.getReview(contractId)).thenReturn(Optional.of(review), Optional.of(review));

        service.decideIssue(contractId, issueId, Map.of("status", "accepted"), member);

        ArgumentCaptor<Map<String, Object>> contractCaptor = ArgumentCaptor.forClass(Map.class);
        verify(repository).saveContract(contractCaptor.capture());
        assertEquals("reviewing", contractCaptor.getValue().get("status"));
    }

    @Test
    void chatContractPreservesExistingIssueStatusesAndDefaultsNewToPending() {
        String contractId = "c-3";
        when(repository.getContract(contractId)).thenReturn(Optional.of(contract(contractId)));
        when(repository.getReview(contractId)).thenReturn(Optional.of(reviewWithIssues(List.of(issue("ruleA-10-1", "accepted")))));
        when(agentGateway.chat(anyMap())).thenReturn(Map.of(
                "answer", "ok",
                "review_result", reviewResult()
        ));

        service.chatContract(contractId, Map.of("message", "recheck"), member);

        ArgumentCaptor<List<Map<String, Object>>> issuesCaptor = ArgumentCaptor.forClass(List.class);
        verify(repository).saveReview(eq(contractId), anyMap(), anyString(), anyList(), anyList(), issuesCaptor.capture(), any());

        Map<String, Object> first = issuesCaptor.getValue().stream().filter(i -> "ruleA-10-1".equals(i.get("id"))).findFirst().orElseThrow();
        Map<String, Object> second = issuesCaptor.getValue().stream().filter(i -> "ruleB-20-2".equals(i.get("id"))).findFirst().orElseThrow();
        assertEquals("accepted", first.get("status"));
        assertEquals("pending", second.get("status"));
    }

    @Test
    void decideIssueReturnsAutoRedraftFailureSemanticsWhenRedraftFails() {
        String contractId = "c-4";
        String issueId = "iss-1";
        Map<String, Object> review = reviewWithIssues(new ArrayList<>(List.of(issue(issueId, "pending"))));
        when(repository.getContract(contractId)).thenReturn(Optional.of(contract(contractId)));
        when(repository.getReview(contractId)).thenReturn(Optional.of(review), Optional.of(review));
        when(agentGateway.redraft(anyString(), anyString(), anyString(), anyList())).thenThrow(new RuntimeException("boom"));

        Map<String, Object> result = service.decideIssue(contractId, issueId,
                Map.of("status", "accepted", "auto_redraft", true), member);

        Map<String, Object> autoRedraft = (Map<String, Object>) result.get("autoRedraft");
        assertNotNull(autoRedraft);
        assertEquals(true, autoRedraft.get("attempted"));
        assertEquals(false, autoRedraft.get("succeeded"));
        assertEquals("RuntimeException", autoRedraft.get("error"));
        verify(repository).saveReview(anyString(), anyMap(), anyString(), anyList(), anyList(), anyList(), any());
    }

    private Map<String, Object> contract(String id) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("id", id);
        out.put("title", "t");
        out.put("type", "采购合同");
        out.put("status", "pending");
        out.put("author", "a");
        out.put("owner_username", "u1");
        out.put("content", "contract text");
        out.put("source_file_name", "a.docx");
        out.put("created_at", OffsetDateTime.now().minusDays(1));
        out.put("updated_at", OffsetDateTime.now().minusHours(1));
        return out;
    }

    private Map<String, Object> reviewWithIssues(List<Map<String, Object>> issues) {
        return new LinkedHashMap<>(Map.of(
                "contract_id", "c",
                "summary", Map.of("contract_type", "采购合同", "overall_risk", "medium"),
                "report_overview", "overview",
                "key_findings", List.of(),
                "next_actions", List.of(),
                "issues", issues,
                "generated_at", OffsetDateTime.now()
        ));
    }

    private Map<String, Object> issue(String id, String status) {
        return new LinkedHashMap<>(Map.of(
                "id", id,
                "type", "risk",
                "severity", "high",
                "message", "m",
                "suggestion", "s",
                "location", "loc",
                "status", status,
                "startIndex", 1,
                "endIndex", 2
        ));
    }

    private Map<String, Object> reviewResult() {
        return new LinkedHashMap<>(Map.of(
                "summary", Map.of("contract_type", "采购合同", "overall_risk", "high"),
                "risks", List.of(
                        Map.of("rule_id", "ruleA", "start_offset", 10, "end_offset", 20, "risk_domain", "合规", "severity", "high",
                                "title", "A", "suggestion", "fix A", "clause_no", "1", "section_title", "S1"),
                        Map.of("rule_id", "ruleB", "start_offset", 20, "end_offset", 30, "risk_domain", "履约", "severity", "medium",
                                "title", "B", "suggestion", "fix B", "clause_no", "2", "section_title", "S2")
                ),
                "report", Map.of("overview", "ov", "key_findings", List.of(), "next_actions", List.of(), "generated_at", OffsetDateTime.now().toString())
        ));
    }
}
