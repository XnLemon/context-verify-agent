package com.example.contract.repository;

import com.example.contract.model.TemplateClause;
import com.example.contract.util.Jsons;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public class TemplateClauseRepository {
    private final JdbcTemplate jdbc;

    public TemplateClauseRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<TemplateClause> list(String search, List<Integer> tagIds, int offset, int limit) {
        String sql = "select * from template_clauses where is_deleted=false";
        if (search != null && !search.isBlank()) {
            sql += " and title ilike ?";
        }
        sql += " order by updated_at desc limit ? offset ?";
        return jdbc.query(sql, ps -> {
            int i = 1;
            if (search != null && !search.isBlank()) {
                ps.setString(i++, "%" + search + "%");
            }
            ps.setInt(i++, limit);
            ps.setInt(i, offset);
        }, this::toClause);
    }

    public Optional<TemplateClause> getById(String id) {
        List<TemplateClause> rows = jdbc.query("select * from template_clauses where id=? and is_deleted=false",
                this::toClause, id);
        return rows.stream().findFirst();
    }

    public void insert(TemplateClause c) {
        jdbc.update("insert into template_clauses(id,title,content,tags,created_by,updated_by,created_at,updated_at) values (?,?,?,cast(? as jsonb),?,?,now(),now())",
                c.id(), c.title(), c.content(), toJsonArray(c.tags()), c.createdBy(), c.updatedBy());
    }

    public void update(TemplateClause c) {
        jdbc.update("update template_clauses set title=?,content=?,tags=cast(? as jsonb),updated_by=?,updated_at=now() where id=?",
                c.title(), c.content(), toJsonArray(c.tags()), c.updatedBy(), c.id());
    }

    public void softDelete(String id) {
        jdbc.update("update template_clauses set is_deleted=true,updated_at=now() where id=?", id);
    }

    private TemplateClause toClause(ResultSet rs, int i) throws SQLException {
        String tagsJson = rs.getString("tags");
        List<Integer> tagIds;
        try {
            tagIds = Jsons.MAPPER.readValue(tagsJson,
                    Jsons.MAPPER.getTypeFactory().constructCollectionType(List.class, Integer.class));
        } catch (Exception e) {
            throw new RuntimeException("Failed to parse tags JSON: " + tagsJson, e);
        }
        return new TemplateClause(
                rs.getString("id"),
                rs.getString("title"),
                rs.getString("content"),
                tagIds,
                rs.getObject("created_by", Integer.class),
                rs.getObject("updated_by", Integer.class),
                rs.getObject("created_at", OffsetDateTime.class),
                rs.getObject("updated_at", OffsetDateTime.class),
                rs.getBoolean("is_deleted")
        );
    }

    private String toJsonArray(List<Integer> ids) {
        if (ids == null || ids.isEmpty()) return "[]";
        return ids.stream().map(String::valueOf).collect(java.util.stream.Collectors.joining(",", "[", "]"));
    }
}
