package com.example.contract.model;

import java.time.OffsetDateTime;
import java.util.List;

public record TemplateClause(
        String id,
        String title,
        String content,
        List<Integer> tags,
        Integer createdBy,
        Integer updatedBy,
        OffsetDateTime createdAt,
        OffsetDateTime updatedAt,
        boolean isDeleted
) {}
