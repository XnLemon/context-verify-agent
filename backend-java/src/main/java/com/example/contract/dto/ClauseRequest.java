package com.example.contract.dto;

import jakarta.validation.constraints.NotBlank;

import java.util.List;

public record ClauseRequest(
        @NotBlank String title,
        @NotBlank String content,
        List<Integer> tags
) {}
