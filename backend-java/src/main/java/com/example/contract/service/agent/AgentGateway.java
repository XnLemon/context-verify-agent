package com.example.contract.service.agent;

import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Map;

public interface AgentGateway {
    Map<String, Object> health();
    Map<String, Object> parseFile(String fileName, byte[] content);
    Map<String, Object> reviewText(String contractText, String contractType, String ourSide);
    Map<String, Object> reviewFile(String fileName, byte[] content, String contractType, String ourSide);
    Map<String, Object> chat(Map<String, Object> payload);
    String redraft(String contractText, String contractType, String ourSide, List<Map<String, String>> acceptedIssues);
}
