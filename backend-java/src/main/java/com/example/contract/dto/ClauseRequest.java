package com.example.contract.dto;

import java.util.List;

public record ClauseRequest(
        String title,
        String content,
        List<Integer> tags
) {}
