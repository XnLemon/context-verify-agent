package com.example.contract.dto;

import java.util.List;

public record TemplateRequest(
        String name,
        String description,
        String content,
        List<Integer> tags
) {}
