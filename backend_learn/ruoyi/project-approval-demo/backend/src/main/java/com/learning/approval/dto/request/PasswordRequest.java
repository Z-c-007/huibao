package com.learning.approval.dto.request;

import jakarta.validation.constraints.*;

public record PasswordRequest(
    @NotBlank @Size(max = 100) String oldPassword,
    @NotBlank @Size(min = 12, max = 64) String newPassword
) {
    @Override
    public String toString() {
        return "PasswordRequest[<redacted>]";
    }
}
