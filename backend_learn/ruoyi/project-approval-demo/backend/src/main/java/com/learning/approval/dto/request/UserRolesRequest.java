package com.learning.approval.dto.request;

import jakarta.validation.constraints.*;
import java.util.List;

public record UserRolesRequest(
    @NotNull @Size(min = 1, max = 20) List<@Positive @NotNull Long> roleIds
) {}
