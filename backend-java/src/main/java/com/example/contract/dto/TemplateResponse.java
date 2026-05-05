package com.example.contract.dto;

import java.util.List;

public record TemplateResponse(
        String id,
        String name,
        String description,
        String content,
        List<TagResponse> tags,
        String createdBy,
        String updatedBy,
        String createdAt,
        String updatedAt
) {}
