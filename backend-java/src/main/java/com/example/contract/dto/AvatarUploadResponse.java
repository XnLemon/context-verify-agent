package com.example.contract.dto;

public record AvatarUploadResponse(
        String avatarUrl,
        MemberResponse member
) {}
