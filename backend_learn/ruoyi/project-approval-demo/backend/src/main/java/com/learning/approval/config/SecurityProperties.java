package com.learning.approval.config;

import jakarta.validation.constraints.*;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

/** 安全参数独立集中配置，不散落在Controller中。密钥使用至少64字节的Base64值。 */
@Validated
@ConfigurationProperties(prefix = "app.security")
public record SecurityProperties(
    @NotBlank String secretBase64,
    @NotBlank String issuer,
    @Min(5) int tokenMinutes,
    @Min(5) int sessionIdleMinutes,
    @Min(1) int refreshThresholdMinutes,
    @Min(1) int maxLoginFailures,
    @Min(30) int loginLockSeconds,
    @NotBlank String redisPrefix
) {}
