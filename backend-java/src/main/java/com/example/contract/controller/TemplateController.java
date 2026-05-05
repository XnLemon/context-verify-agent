package com.example.contract.controller;

import com.example.contract.dto.*;
import com.example.contract.model.Member;
import com.example.contract.service.auth.AuthorizationService;
import com.example.contract.service.template.TemplateService;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
public class TemplateController {
    private final TemplateService templateService;
    private final AuthorizationService authorizationService;

    public TemplateController(TemplateService templateService, AuthorizationService authorizationService) {
        this.templateService = templateService;
        this.authorizationService = authorizationService;
    }

    // === Tags ===
    @GetMapping("/api/tags")
    public List<TagResponse> listTags() {
        return templateService.listTags();
    }

    @PostMapping("/api/tags")
    public TagResponse createTag(@RequestHeader("authorization") String auth, @RequestBody TagRequest req) {
        authorizationService.requireTemplateEditor(auth);
        return templateService.createTag(req);
    }

    @PutMapping("/api/tags/{id}")
    public TagResponse updateTag(@RequestHeader("authorization") String auth, @PathVariable int id, @RequestBody TagRequest req) {
        authorizationService.requireTemplateEditor(auth);
        return templateService.updateTag(id, req);
    }

    @DeleteMapping("/api/tags/{id}")
    public void deleteTag(@RequestHeader("authorization") String auth, @PathVariable int id) {
        authorizationService.requireTemplateEditor(auth);
        templateService.deleteTag(id);
    }

    // === Templates ===
    @GetMapping("/api/templates")
    public List<TemplateResponse> listTemplates(
            @RequestParam(defaultValue = "") String search,
            @RequestParam(required = false) List<Integer> tagIds,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size) {
        return templateService.listTemplates(search, tagIds, page, size);
    }

    @GetMapping("/api/templates/{id}")
    public TemplateResponse getTemplate(@PathVariable String id) {
        return templateService.getTemplate(id);
    }

    @PostMapping("/api/templates")
    public TemplateResponse createTemplate(@RequestHeader("authorization") String auth, @RequestBody TemplateRequest req) {
        Member member = authorizationService.requireTemplateEditor(auth);
        return templateService.createTemplate(req, member.id());
    }

    @PutMapping("/api/templates/{id}")
    public TemplateResponse updateTemplate(@RequestHeader("authorization") String auth,
                                           @PathVariable String id, @RequestBody TemplateRequest req) {
        Member member = authorizationService.requireTemplateEditor(auth);
        return templateService.updateTemplate(id, req, member.id());
    }

    @DeleteMapping("/api/templates/{id}")
    public void deleteTemplate(@RequestHeader("authorization") String auth, @PathVariable String id) {
        Member member = authorizationService.requireTemplateEditor(auth);
        templateService.deleteTemplate(id);
    }

    // === Clauses ===
    @GetMapping("/api/clauses")
    public List<ClauseResponse> listClauses(
            @RequestParam(defaultValue = "") String search,
            @RequestParam(required = false) List<Integer> tagIds,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size) {
        return templateService.listClauses(search, tagIds, page, size);
    }

    @GetMapping("/api/clauses/{id}")
    public ClauseResponse getClause(@PathVariable String id) {
        return templateService.getClause(id);
    }

    @PostMapping("/api/clauses")
    public ClauseResponse createClause(@RequestHeader("authorization") String auth, @RequestBody ClauseRequest req) {
        Member member = authorizationService.requireTemplateEditor(auth);
        return templateService.createClause(req, member.id());
    }

    @PutMapping("/api/clauses/{id}")
    public ClauseResponse updateClause(@RequestHeader("authorization") String auth,
                                       @PathVariable String id, @RequestBody ClauseRequest req) {
        Member member = authorizationService.requireTemplateEditor(auth);
        return templateService.updateClause(id, req, member.id());
    }

    @DeleteMapping("/api/clauses/{id}")
    public void deleteClause(@RequestHeader("authorization") String auth, @PathVariable String id) {
        Member member = authorizationService.requireTemplateEditor(auth);
        templateService.deleteClause(id);
    }
}
