package com.learning.approval.dto.request;

import jakarta.validation.constraints.*;
import java.util.List;

public record RolePermissionsRequest(
    @NotNull @Size(max = 100) List<@NotBlank @Size(max = 80) String> permissions
) {}
