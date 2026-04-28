package com.example.contract.dto;

public record RedraftResponse(
        ContractResponse contract,
        ReviewResultResponse latestReview,
        int acceptedIssueCount
) {}
