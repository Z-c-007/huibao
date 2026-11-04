package com.learning.approval.security;

import java.time.Instant;

public record VerifiedToken(String sessionId, long userId, long authVersion, Instant expiresAt) {}
