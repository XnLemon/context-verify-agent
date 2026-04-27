package com.example.contract.dto;

import java.util.List;

public record ContractListResponse(
        List<ContractResponse> items,
        int total
) {}
