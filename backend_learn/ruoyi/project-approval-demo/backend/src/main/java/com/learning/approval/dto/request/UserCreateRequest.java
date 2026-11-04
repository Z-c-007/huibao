package com.learning.approval.dto.request;

import jakarta.validation.constraints.*;
import java.util.List;

public record UserCreateRequest(
    @NotBlank @Pattern(regexp = "[A-Za-z0-9_]{3,30}") String username,
    @NotBlank @Size(max = 50) String displayName,
    @NotNull @Positive Long orgId,
    @NotBlank @Size(min = 12, max = 64) String password,
    @NotNull @Size(min = 1, max = 20) List<@Positive @NotNull Long> roleIds
) {
    @Override
    public String toString() {
        return "UserCreateRequest[username=" + username + ", password=<redacted>]";
    }
}
