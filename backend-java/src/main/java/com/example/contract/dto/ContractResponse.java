package com.example.contract.dto;

public record ContractResponse(
        String id,
        String title,
        String type,
        String status,
        String updatedAt,
        String author,
        String content
) {}
