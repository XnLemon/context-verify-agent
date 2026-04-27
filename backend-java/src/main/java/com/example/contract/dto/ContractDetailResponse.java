package com.example.contract.dto;

import java.util.List;

public record ContractDetailResponse(
        ContractResponse contract,
        ReviewResultResponse latestReview,
        List<ChatMessageResponse> chatMessages
) {}
