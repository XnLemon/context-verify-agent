package com.example.contract.dto;

import java.util.Map;

public record HistoryResponse(
        String id,
        String type,
        String title,
        String description,
        String createdAt,
        Map<String, String> metadata
) {}
