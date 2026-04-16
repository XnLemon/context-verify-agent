package com.example.contract.repository;

import com.example.contract.model.Member;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public class AuthRepository {
    private final JdbcTemplate jdbc;

    public AuthRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public Optional<MemberRow> findMemberRowByUsername(String username) {
        List<MemberRow> rows = jdbc.query("select * from members where username = ?", this::toMemberRow, username);
        return rows.stream().findFirst();
    }

    public Optional<MemberRow> findMemberRowById(int id) {
        List<MemberRow> rows = jdbc.query("select * from members where id = ?", this::toMemberRow, id);
        return rows.stream().findFirst();
    }

    public Optional<Member> findMemberByToken(String token) {
        List<Member> rows = jdbc.query(
                "select m.* from auth_sessions s join members m on m.id=s.member_id where s.token=? and s.expires_at > now()",
                this::toMember,
                token
        );
        return rows.stream().findFirst();
    }

    public void deleteSessionByToken(String token) {
        jdbc.update("delete from auth_sessions where token = ?", token);
    }

    public String createSession(int memberId, OffsetDateTime expiresAt, String token) {
        jdbc.update("insert into auth_sessions(member_id, token, created_at, expires_at) values (?, ?, now(), ?)", memberId, token, expiresAt);
        return token;
    }

    public void updateMemberLogin(int memberId) {
        jdbc.update("update members set last_login_at=now(), updated_at=now() where id=?", memberId);
    }

    public void insertLoginAudit(int memberId, String ipAddress, String userAgent) {
        jdbc.update("insert into login_audits(member_id, login_at, ip_address, user_agent) values (?, now(), ?, ?)", memberId, ipAddress, userAgent);
    }

    public List<Member> listEmployees() {
        return jdbc.query("select * from members where role='employee' order by created_at desc", this::toMember);
    }

    public int createMember(String username, String displayName, String role, String memberType, String passwordHash, String passwordSalt) {
        return jdbc.queryForObject(
                "insert into members(username, display_name, role, member_type, password_hash, password_salt, is_active, theme_preference, font_scale, notify_enabled, created_at, updated_at) values (?, ?, ?, ?, ?, ?, true, 'system', 'medium', true, now(), now()) returning id",
                Integer.class,
                username, displayName, role, memberType, passwordHash, passwordSalt
        );
    }

    public void updateProfile(int memberId, String displayName) {
        jdbc.update("update members set display_name=?, updated_at=now() where id=?", displayName, memberId);
    }

    public void updateSettings(int memberId, String theme, String fontScale, boolean notifyEnabled) {
        jdbc.update("update members set theme_preference=?, font_scale=?, notify_enabled=?, updated_at=now() where id=?", theme, fontScale, notifyEnabled, memberId);
    }

    public void updateAvatar(int memberId, String avatarUrl) {
        jdbc.update("update members set avatar_url=?, updated_at=now() where id=?", avatarUrl, memberId);
    }

    public boolean hasAdmin() {
        Integer count = jdbc.queryForObject("select count(*) from members where role='admin'", Integer.class);
        return count != null && count > 0;
    }

    public Member toPublic(MemberRow row) {
        return new Member(row.id, row.username, row.displayName, row.role, row.memberType, row.isActive, row.avatarUrl, row.themePreference,
                row.fontScale, row.notifyEnabled, row.createdAt, row.lastLoginAt);
    }

    private MemberRow toMemberRow(ResultSet rs, int i) throws SQLException {
        return new MemberRow(
                rs.getInt("id"),
                rs.getString("username"),
                rs.getString("display_name"),
                rs.getString("role"),
                rs.getString("member_type"),
                rs.getString("password_hash"),
                rs.getString("password_salt"),
                rs.getBoolean("is_active"),
                rs.getString("avatar_url"),
                rs.getString("theme_preference"),
                rs.getString("font_scale"),
                rs.getBoolean("notify_enabled"),
                rs.getObject("created_at", OffsetDateTime.class),
                rs.getObject("last_login_at", OffsetDateTime.class)
        );
    }

    private Member toMember(ResultSet rs, int i) throws SQLException {
        return new Member(
                rs.getInt("id"),
                rs.getString("username"),
                rs.getString("display_name"),
                rs.getString("role"),
                rs.getString("member_type"),
                rs.getBoolean("is_active"),
                rs.getString("avatar_url"),
                rs.getString("theme_preference"),
                rs.getString("font_scale"),
                rs.getBoolean("notify_enabled"),
                rs.getObject("created_at", OffsetDateTime.class),
                rs.getObject("last_login_at", OffsetDateTime.class)
        );
    }

    public record MemberRow(
            int id,
            String username,
            String displayName,
            String role,
            String memberType,
            String passwordHash,
            String passwordSalt,
            boolean isActive,
            String avatarUrl,
            String themePreference,
            String fontScale,
            boolean notifyEnabled,
            OffsetDateTime createdAt,
            OffsetDateTime lastLoginAt
    ) {}
}
