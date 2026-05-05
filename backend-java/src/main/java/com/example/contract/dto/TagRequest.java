package com.example.contract.dto;

import jakarta.validation.constraints.NotBlank;

public record TagRequest(
        @NotBlank String name,
        String color
) {}
