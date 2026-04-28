package com.example.contract.dto;

public record MemberResponse(
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
        String lastLoginAt,
        String createdAt
) {}
