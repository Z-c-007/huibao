package com.learning.approval.exception;

/** 带明确HTTP状态的业务异常，交给统一异常处理器响应。 */
public class BusinessException extends RuntimeException {

    private final int status;

    public BusinessException(int status, String message) {
        super(message);
        this.status = status;
    }

    public int getStatus() {
        return status;
    }

    public static void require(boolean condition, int status, String message) {
        if (!condition) throw new BusinessException(status, message);
    }
}
