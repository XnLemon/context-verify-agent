package com.example.contract.controller;

import com.example.contract.service.agent.AgentGateway;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;

@RestController
public class HealthController {
    private final AgentGateway agentGateway;

    public HealthController(AgentGateway agentGateway) {
        this.agentGateway = agentGateway;
    }

    @GetMapping("/health")
    public Map<String, Object> health() {
        Map<String, Object> agent = agentGateway.health();
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("status", "ok");
        out.put("llm_configured", agent.getOrDefault("llm_configured", false));
        out.put("knowledge_base_ready", agent.getOrDefault("knowledge_base_ready", false));
        return out;
    }
}
