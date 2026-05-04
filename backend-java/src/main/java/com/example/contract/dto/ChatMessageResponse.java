package com.example.contract.dto;

import java.util.List;
import java.util.Map;

public record ChatMessageResponse(
        String id,
        String role,
        String content,
        String timestamp,
        String createdAt,
        List<Map<String, Object>> traceSummary
) {}
