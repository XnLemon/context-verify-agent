package com.example.contract.repository;

import com.example.contract.model.CompanyTemplate;
import com.example.contract.util.Jsons;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public class TemplateRepository {
    private final JdbcTemplate jdbc;

    public TemplateRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<CompanyTemplate> list(String search, List<Integer> tagIds, int offset, int limit) {
        String sql = "select * from company_templates where is_deleted=false";
        if (search != null && !search.isBlank()) {
            sql += " and (name ilike ? or description ilike ?)";
        }
        sql += " order by updated_at desc limit ? offset ?";
        return jdbc.query(sql, ps -> {
            int i = 1;
            if (search != null && !search.isBlank()) {
                String p = "%" + search + "%";
                ps.setString(i++, p);
                ps.setString(i++, p);
            }
            ps.setInt(i++, limit);
            ps.setInt(i, offset);
        }, this::toTemplate);
    }

    public Optional<CompanyTemplate> getById(String id) {
        List<CompanyTemplate> rows = jdbc.query("select * from company_templates where id=? and is_deleted=false",
                this::toTemplate, id);
        return rows.stream().findFirst();
    }

    public void insert(CompanyTemplate t) {
        jdbc.update("insert into company_templates(id,name,description,content,tags,created_by,updated_by,created_at,updated_at) values (?,?,?,?,cast(? as jsonb),?,?,now(),now())",
                t.id(), t.name(), t.description(), t.content(), toJsonArray(t.tags()), t.createdBy(), t.updatedBy());
    }

    public void update(CompanyTemplate t) {
        jdbc.update("update company_templates set name=?,description=?,content=?,tags=cast(? as jsonb),updated_by=?,updated_at=now() where id=?",
                t.name(), t.description(), t.content(), toJsonArray(t.tags()), t.updatedBy(), t.id());
    }

    public void softDelete(String id) {
        jdbc.update("update company_templates set is_deleted=true,updated_at=now() where id=?", id);
    }

    private CompanyTemplate toTemplate(ResultSet rs, int i) throws SQLException {
        String tagsJson = rs.getString("tags");
        List<Integer> tagIds;
        try {
            tagIds = Jsons.MAPPER.readValue(tagsJson,
                    Jsons.MAPPER.getTypeFactory().constructCollectionType(List.class, Integer.class));
        } catch (Exception e) {
            throw new RuntimeException("Failed to parse tags JSON: " + tagsJson, e);
        }
        return new CompanyTemplate(
                rs.getString("id"),
                rs.getString("name"),
                rs.getString("description"),
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
