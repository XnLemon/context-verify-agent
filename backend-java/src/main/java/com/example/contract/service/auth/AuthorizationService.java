package com.example.contract.service.auth;

import com.example.contract.exception.ApiException;
import com.example.contract.model.Member;
import org.springframework.stereotype.Service;

@Service
public class AuthorizationService {
    private final AuthService authService;

    public AuthorizationService(AuthService authService) {
        this.authService = authService;
    }

    public Member requireLoggedIn(String authorization) {
        return authService.authenticate(authorization);
    }

    public Member requireAdmin(String authorization) {
        Member member = requireLoggedIn(authorization);
        if (!"admin".equals(member.role())) {
            throw new ApiException(403, "仅管理员有权限执行该操作");
        }
        return member;
    }

    public Member requireEmployeeOperator(String authorization) {
        Member member = requireLoggedIn(authorization);
        if (!"employee".equals(member.role()) || "legal".equals(member.memberType())) {
            throw new ApiException(403, "仅员工可上传或修改合同");
        }
        return member;
    }

    public Member requireFinalApprover(String authorization) {
        Member member = requireLoggedIn(authorization);
        if ("admin".equals(member.role()) || "legal".equals(member.memberType())) {
            return member;
        }
        throw new ApiException(403, "仅经理/审核可执行最终审批");
    }
}
