package com.example.contract.model;

import java.time.OffsetDateTime;

public record Member(
        int id,
        String username,
        String displayName,
        String role,
        String memberType,
        boolean isActive,
        String avatarUrl,
        String themePreference,
        String fontScale,
        boolean notifyEnabled,
        OffsetDateTime createdAt,
        OffsetDateTime lastLoginAt
) {}
