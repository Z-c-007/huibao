package com.learning.approval.dto.response;

public record ReviewerResponse(
    long id,
    String username,
    String displayName,
    long orgId,
    String orgName
) {}
