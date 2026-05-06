package com.example.contract.dto;

import java.util.List;

public record ClauseResponse(
        String id,
        String title,
        String content,
        List<TagResponse> tags,
        String createdBy,
        String updatedBy,
        String createdAt,
        String updatedAt
) {}
