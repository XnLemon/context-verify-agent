package com.example.contract.dto;

public record IssueResponse(
        String id,
        String type,
        String severity,
        String message,
        String suggestion,
        String location,
        String status,
        Integer startIndex,
        Integer endIndex
) {}
