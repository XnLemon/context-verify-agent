package com.example.contract.model;

import java.time.OffsetDateTime;

public record TemplateTag(
        int id,
        String name,
        String color,
        OffsetDateTime createdAt,
        OffsetDateTime updatedAt
) {}
