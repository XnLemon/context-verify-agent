package com.example.contract.controller;

import com.example.contract.config.AppProperties;
import com.example.contract.exception.ApiException;
import com.example.contract.service.agent.AgentGateway;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.Map;

@RestController
public class CompatController {
    private final AgentGateway agentGateway;
    private final AppProperties props;

    public CompatController(AgentGateway agentGateway, AppProperties props) {
        this.agentGateway = agentGateway;
        this.props = props;
    }

    @PostMapping(value = "/parse", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Map<String, Object> parse(@RequestParam("file") MultipartFile file) throws Exception {
        validateFile(file);
        return agentGateway.parseFile(file.getOriginalFilename(), file.getBytes());
    }

    @PostMapping("/review")
    public Map<String, Object> review(@RequestBody Map<String, Object> payload) {
        return agentGateway.reviewText(
                String.valueOf(payload.getOrDefault("contract_text", "")),
                payload.get("contract_type") == null ? null : payload.get("contract_type").toString(),
                String.valueOf(payload.getOrDefault("our_side", "甲方"))
        );
    }

    @PostMapping(value = "/review/file", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Map<String, Object> reviewFile(@RequestParam("file") MultipartFile file,
                                          @RequestParam(value = "contract_type", required = false) String contractType,
                                          @RequestParam(value = "our_side", defaultValue = "甲方") String ourSide) throws Exception {
        validateFile(file);
        return agentGateway.reviewFile(file.getOriginalFilename(), file.getBytes(), contractType, ourSide);
    }

    @PostMapping("/chat")
    public Map<String, Object> chat(@RequestBody Map<String, Object> payload) {
        return agentGateway.chat(payload);
    }

    private void validateFile(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new ApiException(400, "上传文件不能为空。");
        }
        if (file.getSize() > props.getMaxUploadSizeBytes()) {
            throw new ApiException(400, "上传文件过大，请控制在 5MB 以内。");
        }
        String fileName = file.getOriginalFilename() == null ? "" : file.getOriginalFilename().toLowerCase();
        if (!(fileName.endsWith(".txt") || fileName.endsWith(".docx") || fileName.endsWith(".pdf"))) {
            throw new ApiException(400, "Unsupported file type");
        }
    }
}
