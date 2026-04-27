package com.example.contract.dto;

import java.util.List;

public record EmployeeListResponse(
        List<MemberResponse> items,
        int total
) {}
