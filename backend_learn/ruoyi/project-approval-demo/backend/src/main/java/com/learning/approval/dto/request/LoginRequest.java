package com.learning.approval.dto.request;

import jakarta.validation.constraints.*;

public record LoginRequest(
    @NotBlank @Size(max = 50) String username,
    @NotBlank @Size(max = 100) String password
) {
    @Override
    public String toString() {
        return "LoginRequest[username=" + username + ", password=<redacted>]";
    }
}
