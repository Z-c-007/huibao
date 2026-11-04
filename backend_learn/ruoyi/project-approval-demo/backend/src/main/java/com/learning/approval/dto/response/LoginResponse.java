package com.learning.approval.dto.response;

import com.learning.approval.security.CurrentUser;

public record LoginResponse(String token, String tokenType, long expiresIn, CurrentUser user) {}
