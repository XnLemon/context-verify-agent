package com.example.contract.util;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.Map;

public final class Jsons {
    private Jsons() {}

    public static final ObjectMapper MAPPER = new ObjectMapper().findAndRegisterModules();

    public static Map<String, Object> toMap(String json) {
        try {
            return MAPPER.readValue(json, new TypeReference<>() {});
        } catch (Exception e) {
            throw new RuntimeException("JSON parse failed: " + e.getMessage(), e);
        }
    }

    public static String toJson(Object value) {
        try {
            return MAPPER.writeValueAsString(value);
        } catch (Exception e) {
            throw new RuntimeException("JSON serialize failed: " + e.getMessage(), e);
        }
    }
}
