package com.example.contract.controller;

import com.example.contract.config.AppProperties;
import com.example.contract.exception.ApiException;
import com.example.contract.model.Member;
import com.example.contract.service.auth.AuthService;
import com.example.contract.service.auth.AuthorizationService;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
public class AuthController {
    private final AuthService authService;
    private final AuthorizationService authorizationService;
    private final AppProperties props;

    public AuthController(AuthService authService, AuthorizationService authorizationService, AppProperties props) {
        this.authService = authService;
        this.authorizationService = authorizationService;
        this.props = props;
    }

    @PostMapping("/api/auth/login/challenge")
    public Map<String, Object> loginChallenge(@RequestBody Map<String, Object> payload) {
        return authService.issueChallenge(String.valueOf(payload.getOrDefault("username", "")));
    }

    @PostMapping("/api/auth/login")
    public Map<String, Object> login(@RequestBody Map<String, Object> payload, @RequestHeader(value = "user-agent", required = false) String userAgent,
                                     jakarta.servlet.http.HttpServletRequest request) {
        return authService.login(
                String.valueOf(payload.getOrDefault("username", "")),
                String.valueOf(payload.getOrDefault("challenge_token", "")),
                String.valueOf(payload.getOrDefault("password_proof", "")),
                request.getRemoteAddr(),
                userAgent
        );
    }

    @PostMapping("/api/auth/logout")
    public Map<String, String> logout(@RequestHeader(value = "authorization", required = false) String authorization) {
        authService.logout(authorization);
        return Map.of("message", "ok");
    }

    @GetMapping("/api/auth/me")
    public Map<String, Object> me(@RequestHeader(value = "authorization", required = false) String authorization) {
        Member member = authorizationService.requireLoggedIn(authorization);
        return authService.toMemberPublic(member);
    }

    @GetMapping("/api/auth/profile")
    public Map<String, Object> profile(@RequestHeader(value = "authorization", required = false) String authorization) {
        Member member = authorizationService.requireLoggedIn(authorization);
        return authService.getProfile(member.id());
    }

    @PatchMapping("/api/auth/profile")
    public Map<String, Object> updateProfile(@RequestHeader(value = "authorization", required = false) String authorization,
                                             @RequestBody Map<String, Object> payload) {
        Member member = authorizationService.requireLoggedIn(authorization);
        return authService.updateProfile(member.id(), String.valueOf(payload.getOrDefault("display_name", "")));
    }

    @PostMapping(value = "/api/auth/profile/avatar", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Map<String, Object> updateAvatar(@RequestHeader(value = "authorization", required = false) String authorization,
                                            @RequestParam("file") MultipartFile file) throws Exception {
        Member member = authorizationService.requireLoggedIn(authorization);
        if (file.isEmpty()) {
            throw new ApiException(400, "头像文件不能为空。");
        }
        if (file.getSize() > props.getMaxAvatarUploadSizeBytes()) {
            throw new ApiException(400, "头像文件过大，请控制在 2MB 以内。");
        }
        String filename = file.getOriginalFilename() == null ? "avatar.png" : file.getOriginalFilename();
        String lowered = filename.toLowerCase();
        if (!(lowered.endsWith(".jpg") || lowered.endsWith(".jpeg") || lowered.endsWith(".png") || lowered.endsWith(".webp"))) {
            throw new ApiException(400, "头像仅支持 jpg/jpeg/png/webp 格式。");
        }
        Path root = Path.of("uploads", "avatars", String.valueOf(member.id()));
        Files.createDirectories(root);
        String newName = "avatar-" + java.time.OffsetDateTime.now(ZoneOffset.UTC).format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss")) + "-" + UUID.randomUUID().toString().substring(0, 8) + filename.substring(filename.lastIndexOf('.'));
        Path out = root.resolve(newName);
        Files.write(out, file.getBytes());
        String avatarUrl = "/" + out.toString().replace('\\', '/');
        Map<String, Object> updated = authService.updateAvatar(member.id(), avatarUrl);
        return Map.of("avatar_url", avatarUrl, "member", updated);
    }

    @GetMapping("/api/auth/settings")
    public Map<String, Object> settings(@RequestHeader(value = "authorization", required = false) String authorization) {
        Member member = authorizationService.requireLoggedIn(authorization);
        return authService.getProfile(member.id());
    }

    @PatchMapping("/api/auth/settings")
    public Map<String, Object> updateSettings(@RequestHeader(value = "authorization", required = false) String authorization,
                                              @RequestBody Map<String, Object> payload) {
        Member member = authorizationService.requireLoggedIn(authorization);
        return authService.updateSettings(
                member.id(),
                String.valueOf(payload.getOrDefault("theme_preference", "system")),
                String.valueOf(payload.getOrDefault("font_scale", "medium")),
                Boolean.parseBoolean(String.valueOf(payload.getOrDefault("notify_enabled", true)))
        );
    }

    @GetMapping("/api/admin/employees")
    public Map<String, Object> listEmployees(@RequestHeader(value = "authorization", required = false) String authorization) {
        authorizationService.requireAdmin(authorization);
        List<Map<String, Object>> items = authService.listEmployees();
        return Map.of("items", items, "total", items.size());
    }

    @PostMapping("/api/admin/employees")
    public Map<String, Object> createEmployee(@RequestHeader(value = "authorization", required = false) String authorization,
                                              @RequestBody Map<String, Object> payload) {
        authorizationService.requireAdmin(authorization);
        return authService.createEmployee(payload);
    }
}
