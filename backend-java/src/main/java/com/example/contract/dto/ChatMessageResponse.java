package com.example.contract.dto;

public record ChatMessageResponse(
        String id,
        String role,
        String content,
        String timestamp,
        String createdAt
) {}
