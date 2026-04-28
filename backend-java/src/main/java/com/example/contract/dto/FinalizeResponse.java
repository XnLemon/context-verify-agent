package com.example.contract.dto;

public record FinalizeResponse(
        ContractResponse contract,
        int historyCount
) {}
