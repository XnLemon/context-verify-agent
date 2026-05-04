package com.example.contract.service.auth;

import com.example.contract.config.AppProperties;
import com.example.contract.dto.LoginChallengeResponse;
import com.example.contract.dto.LoginResponse;
import com.example.contract.exception.ApiException;
import com.example.contract.model.Member;
import com.example.contract.repository.AuthRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.OffsetDateTime;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class AuthServiceTest {
    private AuthRepository repository;
    private AppProperties props;

    @BeforeEach
    void setUp() {
        repository = mock(AuthRepository.class);
        props = new AppProperties();
        when(repository.hasAdmin()).thenReturn(true);
    }

    @Test
    void issueChallengeCleansExpiredEntries() throws Exception {
        props.setAuthChallengeTtlSeconds(0);
        props.setAuthMaxChallenges(1000);
        when(repository.findMemberRowByUsername(anyString())).thenReturn(Optional.empty());
        AuthService service = new AuthService(repository, props);

        service.issueChallenge("alice");
        service.issueChallenge("alice");

        assertEquals(1, challengeSize(service));
    }

    @Test
    void issueChallengeRespectsMaxCapacity() throws Exception {
        props.setAuthChallengeTtlSeconds(300);
        props.setAuthMaxChallenges(2);
        when(repository.findMemberRowByUsername(anyString())).thenReturn(Optional.empty());
        AuthService service = new AuthService(repository, props);

        service.issueChallenge("alice");
        service.issueChallenge("alice");
        service.issueChallenge("alice");

        assertEquals(2, challengeSize(service));
    }

    @Test
    void loginProofValidationStillWorks() {
        props.setAuthChallengeTtlSeconds(300);
        props.setAuthMaxChallenges(1000);
        AuthRepository.MemberRow memberRow = new AuthRepository.MemberRow(
                7, "alice", "Alice", "employee", "legal",
                "abc123hash", "salt123", true, null, "system", "medium", true,
                OffsetDateTime.now().minusDays(1), null
        );
        when(repository.findMemberRowByUsername("alice")).thenReturn(Optional.of(memberRow));
        when(repository.findMemberRowById(7)).thenReturn(Optional.of(memberRow));
        when(repository.toPublic(memberRow)).thenReturn(new Member(
                7, "alice", "Alice", "employee", "legal", true,
                null, "system", "medium", true, OffsetDateTime.now().minusDays(1), null
        ));

        AuthService service = new AuthService(repository, props);
        LoginChallengeResponse challenge = service.issueChallenge("alice");
        String nonce = challenge.nonce();
        String challengeToken = challenge.challengeToken();
        String proof = sha256(nonce + ":" + memberRow.passwordHash());

        LoginResponse ok = service.login("alice", challengeToken, proof, "127.0.0.1", "junit");
        assertNotNull(ok.token());

        LoginChallengeResponse challenge2 = service.issueChallenge("alice");
        ApiException ex = assertThrows(ApiException.class,
                () -> service.login("alice", challenge2.challengeToken(), proof + "bad", "127.0.0.1", "junit"));
        assertEquals(401, ex.getStatus());
    }

    @SuppressWarnings("unchecked")
    private int challengeSize(AuthService service) throws Exception {
        Field field = AuthService.class.getDeclaredField("challenges");
        field.setAccessible(true);
        Map<String, Object> challenges = (Map<String, Object>) field.get(service);
        return challenges.size();
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
}
