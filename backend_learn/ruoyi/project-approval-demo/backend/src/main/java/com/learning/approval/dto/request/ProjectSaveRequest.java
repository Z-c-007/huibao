package com.learning.approval.dto.request;

import jakarta.validation.constraints.*;
import java.math.BigDecimal;

/** 作者、单位、状态不接受客户端指定，防止批量属性赋值越权。 */
public record ProjectSaveRequest(
    @NotBlank @Size(max = 100) String name,
    @NotBlank
    @Pattern(
        regexp = "[A-Za-z0-9][A-Za-z0-9_-]{2,39}",
        message = "编号须为3至40位字母、数字、下划线或短横线"
    )
    String code,
    @NotNull @DecimalMin("0") @Digits(integer = 12, fraction = 2) BigDecimal amount,
    @NotBlank @Size(max = 4000) String material,
    @NotNull @Min(0) Long version
) {}
