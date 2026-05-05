package com.example.contract.model;

import java.time.OffsetDateTime;
import java.util.List;

public record CompanyTemplate(
        String id,
        String name,
        String description,
        String content,
        List<Integer> tags,
        Integer createdBy,
        Integer updatedBy,
        OffsetDateTime createdAt,
        OffsetDateTime updatedAt,
        boolean isDeleted
) {}
