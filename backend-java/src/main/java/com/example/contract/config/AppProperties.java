package com.example.contract.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "app")
public class AppProperties {
    private String defaultContractType = "采购合同";
    private long maxUploadSizeBytes = 5 * 1024 * 1024;
    private long maxAvatarUploadSizeBytes = 2 * 1024 * 1024;
    private int authSessionTtlHours = 72;
    private int authChallengeTtlSeconds = 90;
    private int authMaxChallenges = 1000;
    private String bootstrapAdminUsername = "admin";
    private String bootstrapAdminPassword = "admin123";
    private String bootstrapAdminDisplayName = "系统管理员";
    private Agent agent = new Agent();

    public static class Agent {
        private Rpc rpc = new Rpc();
        public Rpc getRpc() { return rpc; }
        public void setRpc(Rpc rpc) { this.rpc = rpc; }
    }

    public static class Rpc {
        private String provider = "grpc";
        private String grpcTarget = "127.0.0.1:50051";
        private long timeoutMillis = 15000;

        public String getProvider() { return provider; }
        public void setProvider(String provider) { this.provider = provider; }
        public String getGrpcTarget() { return grpcTarget; }
        public void setGrpcTarget(String grpcTarget) { this.grpcTarget = grpcTarget; }
        public long getTimeoutMillis() { return timeoutMillis; }
        public void setTimeoutMillis(long timeoutMillis) { this.timeoutMillis = timeoutMillis; }
    }

    public String getDefaultContractType() { return defaultContractType; }
    public void setDefaultContractType(String defaultContractType) { this.defaultContractType = defaultContractType; }
    public long getMaxUploadSizeBytes() { return maxUploadSizeBytes; }
    public void setMaxUploadSizeBytes(long maxUploadSizeBytes) { this.maxUploadSizeBytes = maxUploadSizeBytes; }
    public long getMaxAvatarUploadSizeBytes() { return maxAvatarUploadSizeBytes; }
    public void setMaxAvatarUploadSizeBytes(long maxAvatarUploadSizeBytes) { this.maxAvatarUploadSizeBytes = maxAvatarUploadSizeBytes; }
    public int getAuthSessionTtlHours() { return authSessionTtlHours; }
    public void setAuthSessionTtlHours(int authSessionTtlHours) { this.authSessionTtlHours = authSessionTtlHours; }
    public int getAuthChallengeTtlSeconds() { return authChallengeTtlSeconds; }
    public void setAuthChallengeTtlSeconds(int authChallengeTtlSeconds) { this.authChallengeTtlSeconds = authChallengeTtlSeconds; }
    public int getAuthMaxChallenges() { return authMaxChallenges; }
    public void setAuthMaxChallenges(int authMaxChallenges) { this.authMaxChallenges = authMaxChallenges; }
    public String getBootstrapAdminUsername() { return bootstrapAdminUsername; }
    public void setBootstrapAdminUsername(String bootstrapAdminUsername) { this.bootstrapAdminUsername = bootstrapAdminUsername; }
    public String getBootstrapAdminPassword() { return bootstrapAdminPassword; }
    public void setBootstrapAdminPassword(String bootstrapAdminPassword) { this.bootstrapAdminPassword = bootstrapAdminPassword; }
    public String getBootstrapAdminDisplayName() { return bootstrapAdminDisplayName; }
    public void setBootstrapAdminDisplayName(String bootstrapAdminDisplayName) { this.bootstrapAdminDisplayName = bootstrapAdminDisplayName; }
    public Agent getAgent() { return agent; }
    public void setAgent(Agent agent) { this.agent = agent; }
}
