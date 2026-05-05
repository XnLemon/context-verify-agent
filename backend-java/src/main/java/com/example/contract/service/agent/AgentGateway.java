package com.example.contract.service.agent;

import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Map;
import java.util.Iterator;

public interface AgentGateway {
    record ChatStreamEvent(String event, String dataJson) {}

    Map<String, Object> health();
    Map<String, Object> parseFile(String fileName, byte[] content);
    Map<String, Object> reviewText(String contractText, String contractType, String ourSide);
    Map<String, Object> reviewFile(String fileName, byte[] content, String contractType, String ourSide);
    Map<String, Object> chat(Map<String, Object> payload);
    Iterator<ChatStreamEvent> chatStream(Map<String, Object> payload);
    String redraft(String contractText, String contractType, String ourSide, List<Map<String, String>> acceptedIssues);

    Map<String, Object> embedDocument(String text, String docId, String sourceType, String title);
}
