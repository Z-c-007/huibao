package com.learning.approval.common;

import org.slf4j.MDC;

/** HTTP响应外壳。Java对象最终由Spring MVC/Jackson序列化为JSON。 */
public record ApiResponse<T>(int code, String msg, T data, String requestId) {
    public static <T> ApiResponse<T> success(T data) {
        return new ApiResponse<>(200, "操作成功", data, MDC.get("requestId"));
    }

    public static ApiResponse<Void> error(int code, String message) {
        return new ApiResponse<>(code, message, null, MDC.get("requestId"));
    }
}
