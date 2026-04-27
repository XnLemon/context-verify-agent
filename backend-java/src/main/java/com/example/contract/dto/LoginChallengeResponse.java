package com.example.contract.dto;

public record LoginChallengeResponse(
        String challengeToken,
        String nonce,
        String salt,
        String expiresAt
) {}
