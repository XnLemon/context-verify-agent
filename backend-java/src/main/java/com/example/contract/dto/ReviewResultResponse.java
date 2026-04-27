package com.example.contract.dto;

import java.util.List;
import java.util.Map;

public record ReviewResultResponse(
        Map<String, Object> summary,
        String reportOverview,
        List<String> keyFindings,
        List<String> nextActions,
        List<IssueResponse> issues,
        String generatedAt
) {}
