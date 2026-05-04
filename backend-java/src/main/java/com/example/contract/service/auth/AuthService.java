package com.example.contract.service.auth;

import com.example.contract.config.AppProperties;
import com.example.contract.dto.EmployeeListResponse;
import com.example.contract.dto.LoginChallengeResponse;
import com.example.contract.dto.LoginResponse;
import com.example.contract.dto.MemberResponse;
import com.example.contract.exception.ApiException;
import com.example.contract.model.Member;
import com.example.contract.repository.AuthRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.time.OffsetDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class AuthService {
    private static final Logger log = LoggerFactory.getLogger(AuthService.class);
    private static final SecureRandom SECURE_RANDOM = new SecureRandom();
    private final AuthRepository repository;
    private final AppProperties props;
    private final Map<String, LoginChallenge> challenges = new ConcurrentHashMap<>();

    public AuthService(AuthRepository repository, AppProperties props) {
        this.repository = repository;
        this.props = props;
        bootstrapAdmin();
    }

    public LoginChallengeResponse issueChallenge(String username) {
        cleanupChallenges(OffsetDateTime.now());
        String normalized = trim(username);
        if (normalized.isEmpty()) {
            throw new ApiException(401, "用户名或密码错误");
        }

        Optional<AuthRepository.MemberRow> memberOpt = repository.findMemberRowByUsername(normalized);
        String salt = randomHex(16);
        String passwordHash = randomHex(32);
        Integer memberId = null;
        if (memberOpt.isPresent() && memberOpt.get().isActive()) {
            salt = memberOpt.get().passwordSalt();
            passwordHash = memberOpt.get().passwordHash();
            memberId = memberOpt.get().id();
        }

        String challengeToken = generateOpaqueToken();
        String nonce = generateOpaqueToken();
        OffsetDateTime now = OffsetDateTime.now();
        OffsetDateTime expiresAt = now.plusSeconds(props.getAuthChallengeTtlSeconds());
        challenges.put(challengeToken, new LoginChallenge(normalized, nonce, passwordHash, memberId, now, expiresAt));
        cleanupChallenges(now);

        return new LoginChallengeResponse(challengeToken, nonce, salt, expiresAt.toString());
    }

    public LoginResponse login(String username, String challengeToken, String passwordProof, String ipAddress, String userAgent) {
        cleanupChallenges(OffsetDateTime.now());
        String normalized = trim(username);
        if (normalized.isEmpty() || trim(challengeToken).isEmpty() || trim(passwordProof).isEmpty()) {
            throw new ApiException(401, "用户名或密码错误");
        }

        LoginChallenge challenge = challenges.remove(challengeToken);
        if (challenge == null || challenge.expiresAt().isBefore(OffsetDateTime.now()) || !challenge.username().equals(normalized)) {
            throw new ApiException(401, "用户名或密码错误");
        }

        String expected = sha256(challenge.nonce() + ":" + challenge.passwordHash());
        if (!constantTimeEquals(expected, passwordProof) || challenge.memberId() == null) {
            throw new ApiException(401, "用户名或密码错误");
        }

        AuthRepository.MemberRow member = repository.findMemberRowById(challenge.memberId())
                .filter(AuthRepository.MemberRow::isActive)
                .orElseThrow(() -> new ApiException(401, "用户名或密码错误"));

        String token = generateOpaqueToken();
        OffsetDateTime expiresAt = OffsetDateTime.now().plusHours(props.getAuthSessionTtlHours());
        repository.updateMemberLogin(member.id());
        repository.createSession(member.id(), expiresAt, token);
        repository.insertLoginAudit(member.id(), ipAddress, userAgent);

        return new LoginResponse(token, expiresAt.toString(), toMemberPublic(repository.toPublic(member)));
    }

    public void logout(String authorization) {
        String token = bearerToken(authorization);
        if (token != null) {
            repository.deleteSessionByToken(token);
        }
    }

    public Member authenticate(String authorization) {
        String token = bearerToken(authorization);
        if (token == null || token.isBlank()) {
            throw new ApiException(401, "缺少登录凭证");
        }
        return repository.findMemberByToken(token)
                .filter(Member::isActive)
                .orElseThrow(() -> new ApiException(401, "登录已失效，请重新登录"));
    }

    public EmployeeListResponse listEmployees() {
        List<MemberResponse> items = repository.listEmployees().stream().map(this::toMemberPublic).toList();
        return new EmployeeListResponse(items, items.size());
    }

    public MemberResponse createEmployee(Map<String, Object> payload) {
        String username = trim((String) payload.get("username"));
        String displayName = trim((String) payload.get("displayName"));
        String password = trim((String) payload.get("password"));
        String memberType = trim((String) payload.getOrDefault("memberType", "legal"));

        if (username.isEmpty() || displayName.isEmpty() || password.isEmpty()) {
            throw new ApiException(400, "用户名、昵称和密码不能为空");
        }
        if (!Set.of("legal", "procurement", "business", "other", "admin").contains(memberType)) {
            throw new ApiException(400, "无效的成员类型");
        }
        if (repository.findMemberRowByUsername(username).isPresent()) {
            throw new ApiException(400, "用户名已存在");
        }

        String salt = randomHex(16);
        String hash = sha256(salt + ":" + password);
        int id = repository.createMember(username, displayName, "employee", memberType, hash, salt);
        Member member = repository.findMemberRowById(id).map(repository::toPublic).orElseThrow();
        return toMemberPublic(member);
    }

    public MemberResponse getProfile(int memberId) {
        Member member = repository.findMemberRowById(memberId).map(repository::toPublic)
                .orElseThrow(() -> new ApiException(401, "登录已失效，请重新登录"));
        return toMemberPublic(member);
    }

    public MemberResponse updateProfile(int memberId, String displayName) {
        if (trim(displayName).isEmpty()) {
            throw new ApiException(400, "昵称不能为空");
        }
        repository.updateProfile(memberId, displayName.trim());
        return getProfile(memberId);
    }

    public MemberResponse updateSettings(int memberId, String themePreference, String fontScale, boolean notifyEnabled) {
        repository.updateSettings(memberId, themePreference, fontScale, notifyEnabled);
        return getProfile(memberId);
    }

    public MemberResponse updateAvatar(int memberId, String avatarUrl) {
        repository.updateAvatar(memberId, avatarUrl);
        return getProfile(memberId);
    }

    public MemberResponse toMemberPublic(Member member) {
        return new MemberResponse(
                member.id(),
                member.username(),
                member.displayName(),
                member.role(),
                member.memberType(),
                member.isActive(),
                member.avatarUrl(),
                member.themePreference(),
                member.fontScale(),
                member.notifyEnabled(),
                member.lastLoginAt() == null ? null : member.lastLoginAt().toString(),
                member.createdAt() == null ? "" : member.createdAt().toString()
        );
    }

    private void bootstrapAdmin() {
        if (repository.hasAdmin()) {
            return;
        }
        String salt = randomHex(16);
        String hash = sha256(salt + ":" + props.getBootstrapAdminPassword());
        repository.createMember(props.getBootstrapAdminUsername(), props.getBootstrapAdminDisplayName(), "admin", "admin", hash, salt);
    }

    private String bearerToken(String authorization) {
        if (authorization == null || !authorization.toLowerCase(Locale.ROOT).startsWith("bearer ")) {
            return null;
        }
        return authorization.substring(7).trim();
    }

    private String trim(String value) {
        return value == null ? "" : value.trim();
    }

    private String sha256(String source) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] digest = md.digest(source.getBytes(StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder();
            for (byte b : digest) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString();
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    private String randomHex(int bytes) {
        byte[] data = new byte[bytes];
        SECURE_RANDOM.nextBytes(data);
        StringBuilder sb = new StringBuilder();
        for (byte b : data) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }

    private String generateOpaqueToken() {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(UUID.randomUUID().toString().getBytes(StandardCharsets.UTF_8));
    }

    private boolean constantTimeEquals(String expected, String actual) {
        byte[] expectedBytes = expected == null ? new byte[0] : expected.getBytes(StandardCharsets.UTF_8);
        byte[] actualBytes = actual == null ? new byte[0] : actual.getBytes(StandardCharsets.UTF_8);
        return MessageDigest.isEqual(expectedBytes, actualBytes);
    }

    private void cleanupChallenges(OffsetDateTime now) {
        int before = challenges.size();
        challenges.entrySet().removeIf(e -> e.getValue().expiresAt().isBefore(now));
        int maxChallenges = Math.max(1, props.getAuthMaxChallenges());
        if (challenges.size() > maxChallenges) {
            List<Map.Entry<String, LoginChallenge>> sorted = new ArrayList<>(challenges.entrySet());
            sorted.sort(Comparator.comparing(e -> e.getValue().issuedAt()));
            int toRemove = challenges.size() - maxChallenges;
            int removed = 0;
            for (Map.Entry<String, LoginChallenge> entry : sorted) {
                if (removed >= toRemove) {
                    break;
                }
                if (challenges.remove(entry.getKey(), entry.getValue())) {
                    removed += 1;
                }
            }
        }
        int after = challenges.size();
        if (after < before) {
            log.debug("Cleaned login challenges: before={}, after={}", before, after);
        }
    }

    record LoginChallenge(String username, String nonce, String passwordHash, Integer memberId, OffsetDateTime issuedAt, OffsetDateTime expiresAt) {}
}
