package com.example.contract.config;

import com.example.contract.service.agent.AgentGateway;
import com.example.contract.service.agent.CustomStubAgentGateway;
import com.example.contract.service.agent.GrpcAgentGateway;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class AgentGatewayConfig {
    @Bean
    public AgentGateway agentGateway(AppProperties props) {
        String provider = props.getAgent().getRpc().getProvider();
        if ("custom".equalsIgnoreCase(provider)) {
            return new CustomStubAgentGateway();
        }
        return new GrpcAgentGateway(props.getAgent().getRpc().getGrpcTarget(), props.getAgent().getRpc().getTimeoutMillis());
    }
}
