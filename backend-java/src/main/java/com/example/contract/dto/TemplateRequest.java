package com.example.contract.dto;

import jakarta.validation.constraints.NotBlank;

import java.util.List;

public record TemplateRequest(
        @NotBlank String name,
        String description,
        @NotBlank String content,
        List<Integer> tags
) {}
