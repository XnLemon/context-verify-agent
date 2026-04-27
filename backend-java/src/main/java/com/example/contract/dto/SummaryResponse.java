package com.example.contract.dto;

public record SummaryResponse(
        int pendingCount,
        double complianceRate,
        int highRiskCount,
        double averageReviewDurationHours,
        int totalContracts
) {}
