package com.example.contract.dto;

import java.util.List;
import java.util.Map;

public record PipelineStatusResponse(
        String pipelineId,
        String mode,
        String status,
        Map<String, Object> report,
        List<Map<String, Object>> agentSummaries
) {}
