package com.learning.approval.security;

import java.time.Instant;

/** Redis保存的登录状态。JWT只携带会话ID、用户ID及版本，不放完整权限列表。 */
public record LoginSession(
    String sessionId,
    CurrentUser user,
    Instant issuedAt,
    Instant absoluteExpiresAt,
    String ip,
    String userAgent
) {}
