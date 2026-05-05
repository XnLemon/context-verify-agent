package com.example.contract.service.template;

import com.example.contract.dto.TagRequest;
import com.example.contract.dto.TemplateRequest;
import com.example.contract.exception.ApiException;
import com.example.contract.model.CompanyTemplate;
import com.example.contract.model.TemplateTag;
import com.example.contract.repository.TemplateClauseRepository;
import com.example.contract.repository.TemplateRepository;
import com.example.contract.repository.TemplateTagRepository;
import com.example.contract.service.agent.AgentGateway;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class TemplateServiceTest {

    @Mock TemplateRepository templateRepo;
    @Mock TemplateClauseRepository clauseRepo;
    @Mock TemplateTagRepository tagRepo;
    @Mock AgentGateway agentGateway;

    @Test
    void createTemplate_shouldInsertAndSyncEmbedding() {
        when(tagRepo.list()).thenReturn(List.of());
        when(agentGateway.embedDocument(anyString(), anyString(), anyString(), anyString()))
                .thenReturn(Map.of("status", "ok"));

        TemplateService service = new TemplateService(templateRepo, clauseRepo, tagRepo, agentGateway);
        TemplateRequest req = new TemplateRequest("Test Template", "desc", "<p>content</p>", List.of());

        var result = service.createTemplate(req, 1);

        assertNotNull(result);
        assertEquals("Test Template", result.name());
        verify(templateRepo).insert(any(CompanyTemplate.class));
        verify(agentGateway).embedDocument(eq("<p>content</p>"), anyString(), eq("template"), eq("Test Template"));
    }

    @Test
    void getTemplate_shouldThrowWhenNotFound() {
        TemplateService service = new TemplateService(templateRepo, clauseRepo, tagRepo, agentGateway);
        when(templateRepo.getById("nonexistent")).thenReturn(Optional.empty());

        assertThrows(ApiException.class,
                () -> service.getTemplate("nonexistent"));
    }

    @Test
    void deleteTemplate_shouldSoftDelete() {
        TemplateService service = new TemplateService(templateRepo, clauseRepo, tagRepo, agentGateway);

        service.deleteTemplate("some-id");

        verify(templateRepo).softDelete("some-id");
    }

    @Test
    void createTag_shouldInsertAndReturn() {
        TemplateService service = new TemplateService(templateRepo, clauseRepo, tagRepo, agentGateway);
        when(tagRepo.list()).thenReturn(List.of(
                new TemplateTag(1, "TestTag", "#ff0000", null, null)
        ));

        var result = service.createTag(new TagRequest("TestTag", "#ff0000"));

        assertNotNull(result);
        assertEquals("TestTag", result.name());
        verify(tagRepo).insert("TestTag", "#ff0000");
    }
}
