package com.example.contract.dto;

public record ScanResponse(
        ContractResponse contract,
        ReviewResultResponse latestReview,
        int historyCount
) {}
