package com.learning.approval.dto.request;

import jakarta.validation.constraints.*;
import java.util.List;

/** requestId由前端生成；网络失败重试时复用，参数改变时重新生成。 */
public record ProjectSubmitRequest(
    @NotNull @Size(max = 50) List<@NotNull @Positive Long> reviewers,
    @NotNull @Min(0) Long version,
    @NotBlank @Pattern(regexp = "[A-Za-z0-9_-]{16,64}") String requestId
) {}
