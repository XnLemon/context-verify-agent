package com.example.contract.service.template;

import com.example.contract.dto.*;
import com.example.contract.exception.ApiException;
import com.example.contract.model.*;
import com.example.contract.repository.*;
import com.example.contract.service.agent.AgentGateway;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.Objects;
import java.util.stream.Collectors;

@Service
public class TemplateService {
    private static final Logger log = LoggerFactory.getLogger(TemplateService.class);
    private final TemplateRepository templateRepo;
    private final TemplateClauseRepository clauseRepo;
    private final TemplateTagRepository tagRepo;
    private final AgentGateway agentGateway;

    public TemplateService(TemplateRepository templateRepo, TemplateClauseRepository clauseRepo,
                           TemplateTagRepository tagRepo, AgentGateway agentGateway) {
        this.templateRepo = templateRepo;
        this.clauseRepo = clauseRepo;
        this.tagRepo = tagRepo;
        this.agentGateway = agentGateway;
    }

    // === Tags ===
    public List<TagResponse> listTags() {
        return tagRepo.list().stream()
                .map(t -> new TagResponse(t.id(), t.name(), t.color()))
                .toList();
    }

    public TagResponse createTag(TagRequest req) {
        int id = tagRepo.insert(req.name(), req.color());
        return new TagResponse(id, req.name(), req.color());
    }

    public TagResponse updateTag(int id, TagRequest req) {
        tagRepo.update(id, req.name(), req.color());
        return new TagResponse(id, req.name(), req.color());
    }

    public void deleteTag(int id) {
        tagRepo.delete(id);
    }

    // === Templates ===
    public List<TemplateResponse> listTemplates(String search, List<Integer> tagIds, int page, int size) {
        int offset = (page - 1) * size;
        return templateRepo.list(search, tagIds, offset, size).stream()
                .map(this::toTemplateResponse)
                .toList();
    }

    public TemplateResponse getTemplate(String id) {
        CompanyTemplate t = templateRepo.getById(id)
                .orElseThrow(() -> new ApiException(404, "模板不存在"));
        return toTemplateResponse(t);
    }

    @Transactional
    public TemplateResponse createTemplate(TemplateRequest req, int memberId) {
        String id = UUID.randomUUID().toString();
        CompanyTemplate t = new CompanyTemplate(id, req.name(), req.description(), req.content(), req.tags(),
                memberId, memberId, null, null, false);
        templateRepo.insert(t);
        syncEmbedding(req.content(), id, "template", req.name());
        return toTemplateResponse(t);
    }

    @Transactional
    public TemplateResponse updateTemplate(String id, TemplateRequest req, int memberId) {
        CompanyTemplate existing = templateRepo.getById(id)
                .orElseThrow(() -> new ApiException(404, "模板不存在"));
        CompanyTemplate updated = new CompanyTemplate(id, req.name(), req.description(), req.content(), req.tags(),
                existing.createdBy(), memberId, existing.createdAt(), null, false);
        templateRepo.update(updated);
        syncEmbedding(req.content(), id, "template", req.name());
        return toTemplateResponse(updated);
    }

    @Transactional
    public void deleteTemplate(String id) {
        templateRepo.softDelete(id);
    }

    // === Clauses ===
    public List<ClauseResponse> listClauses(String search, List<Integer> tagIds, int page, int size) {
        int offset = (page - 1) * size;
        return clauseRepo.list(search, tagIds, offset, size).stream()
                .map(this::toClauseResponse)
                .toList();
    }

    public ClauseResponse getClause(String id) {
        TemplateClause c = clauseRepo.getById(id)
                .orElseThrow(() -> new ApiException(404, "条款不存在"));
        return toClauseResponse(c);
    }

    @Transactional
    public ClauseResponse createClause(ClauseRequest req, int memberId) {
        String id = UUID.randomUUID().toString();
        TemplateClause c = new TemplateClause(id, req.title(), req.content(), req.tags(),
                memberId, memberId, null, null, false);
        clauseRepo.insert(c);
        syncEmbedding(req.content(), id, "clause", req.title());
        return toClauseResponse(c);
    }

    @Transactional
    public ClauseResponse updateClause(String id, ClauseRequest req, int memberId) {
        TemplateClause existing = clauseRepo.getById(id)
                .orElseThrow(() -> new ApiException(404, "条款不存在"));
        TemplateClause updated = new TemplateClause(id, req.title(), req.content(), req.tags(),
                existing.createdBy(), memberId, existing.createdAt(), null, false);
        clauseRepo.update(updated);
        syncEmbedding(req.content(), id, "clause", req.title());
        return toClauseResponse(updated);
    }

    @Transactional
    public void deleteClause(String id) {
        clauseRepo.softDelete(id);
    }

    private void syncEmbedding(String text, String docId, String sourceType, String title) {
        try {
            agentGateway.embedDocument(text, docId, sourceType, title);
        } catch (Exception e) {
            log.error("Embedding sync failed for docId={}, retrying...", docId, e);
            try {
                Thread.sleep(1000);
                agentGateway.embedDocument(text, docId, sourceType, title);
            } catch (Exception e2) {
                log.error("Embedding sync failed after retry for docId={}", docId, e2);
            }
        }
    }

    private TemplateResponse toTemplateResponse(CompanyTemplate t) {
        List<TemplateTag> allTags = tagRepo.list();
        Map<Integer, TemplateTag> tagMap = allTags.stream().collect(Collectors.toMap(TemplateTag::id, tag -> tag));
        List<TagResponse> resolvedTags = t.tags().stream()
                .map(id -> { TemplateTag tag = tagMap.get(id); return tag == null ? null : new TagResponse(tag.id(), tag.name(), tag.color()); })
                .filter(Objects::nonNull)
                .toList();
        return new TemplateResponse(t.id(), t.name(), t.description(), t.content(), resolvedTags,
                String.valueOf(t.createdBy()), String.valueOf(t.updatedBy()),
                String.valueOf(t.createdAt()), String.valueOf(t.updatedAt()));
    }

    private ClauseResponse toClauseResponse(TemplateClause c) {
        List<TemplateTag> allTags = tagRepo.list();
        Map<Integer, TemplateTag> tagMap = allTags.stream().collect(Collectors.toMap(TemplateTag::id, tag -> tag));
        List<TagResponse> resolvedTags = c.tags().stream()
                .map(id -> { TemplateTag tag = tagMap.get(id); return tag == null ? null : new TagResponse(tag.id(), tag.name(), tag.color()); })
                .filter(Objects::nonNull)
                .toList();
        return new ClauseResponse(c.id(), c.title(), c.content(), resolvedTags,
                String.valueOf(c.createdBy()), String.valueOf(c.updatedBy()),
                String.valueOf(c.createdAt()), String.valueOf(c.updatedAt()));
    }
}
