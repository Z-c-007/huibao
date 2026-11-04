package com.learning.approval.dto.request;

import jakarta.validation.constraints.*;

public record WithdrawRequest(
    @NotNull @Min(0) Long version,
    @NotBlank @Size(max = 1000) String reason
) {}
