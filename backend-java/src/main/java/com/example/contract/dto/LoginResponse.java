package com.example.contract.dto;

public record LoginResponse(
        String token,
        String expiresAt,
        MemberResponse member
) {}
