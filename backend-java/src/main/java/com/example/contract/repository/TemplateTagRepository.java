package com.example.contract.repository;

import com.example.contract.model.TemplateTag;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.OffsetDateTime;
import java.util.List;

@Repository
public class TemplateTagRepository {
    private final JdbcTemplate jdbc;

    public TemplateTagRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<TemplateTag> list() {
        return jdbc.query("select * from template_tags order by name", this::toTag);
    }

    public int insert(String name, String color) {
        return jdbc.queryForObject("insert into template_tags(name,color) values (?,?) returning id", Integer.class, name, color);
    }

    public void update(int id, String name, String color) {
        jdbc.update("update template_tags set name=?,color=?,updated_at=now() where id=?", name, color, id);
    }

    public void delete(int id) {
        jdbc.update("delete from template_tags where id=?", id);
    }

    private TemplateTag toTag(ResultSet rs, int i) throws SQLException {
        return new TemplateTag(rs.getInt("id"), rs.getString("name"), rs.getString("color"),
                rs.getObject("created_at", OffsetDateTime.class), rs.getObject("updated_at", OffsetDateTime.class));
    }
}
