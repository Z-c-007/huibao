package com.learning.approval.dto.request;

import jakarta.validation.constraints.*;

public record ProjectReviewRequest(
    @NotBlank @Size(max = 36) String stepId,
    @NotNull @Min(0) Long version,
    @NotNull Boolean approved,
    @NotNull @Size(max = 1000) String opinion
) {}
