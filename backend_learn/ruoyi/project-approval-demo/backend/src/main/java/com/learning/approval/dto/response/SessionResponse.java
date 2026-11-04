package com.learning.approval.dto.response;

import java.time.Instant;

public record SessionResponse(
    String sessionId,
    String ip,
    String userAgent,
    Instant issuedAt,
    Instant absoluteExpiresAt,
    long ttlSeconds,
    boolean current
) {}
