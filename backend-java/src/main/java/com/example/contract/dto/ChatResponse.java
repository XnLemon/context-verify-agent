package com.example.contract.dto;

import java.util.List;

public record ChatResponse(
        String intent,
        String toolUsed,
        ChatMessageResponse assistantMessage,
        List<ChatMessageResponse> messages,
        ReviewResultResponse latestReview
) {}
