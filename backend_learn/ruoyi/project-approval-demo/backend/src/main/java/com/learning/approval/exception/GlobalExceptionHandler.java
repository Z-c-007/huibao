package com.learning.approval.exception;

import com.learning.approval.common.ApiResponse;
import jakarta.validation.ConstraintViolationException;
import java.util.Objects;
import org.slf4j.*;
import org.springframework.dao.*;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.web.bind.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    private ResponseEntity<ApiResponse<Void>> error(int code, String message) {
        return ResponseEntity.status(code).body(ApiResponse.error(code, message));
    }

    @ExceptionHandler(BusinessException.class)
    public Object business(BusinessException e) {
        return error(e.getStatus(), e.getMessage());
    }

    @ExceptionHandler(AccessDeniedException.class)
    public Object denied(AccessDeniedException e) {
        return error(403, "没有此操作权限");
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public Object validation(MethodArgumentNotValidException e) {
        return error(
            400,
            Objects.toString(
                e.getBindingResult().getAllErrors().get(0).getDefaultMessage(),
                "参数不合法"
            )
        );
    }

    @ExceptionHandler({
        HttpMessageNotReadableException.class,
        MethodArgumentTypeMismatchException.class,
        MissingServletRequestParameterException.class,
        ConstraintViolationException.class,
    })
    public Object malformed(Exception e) {
        return error(400, "请求参数格式不正确或缺少必要参数");
    }

    @ExceptionHandler(DataIntegrityViolationException.class)
    public Object integrity(Exception e) {
        log.warn("数据唯一性或引用约束冲突", e);
        return error(409, "编号重复或关联数据冲突，请核对输入");
    }

    @ExceptionHandler(ConcurrencyFailureException.class)
    public Object concurrent(Exception e) {
        log.warn("数据库并发操作冲突", e);
        return error(409, "存在并发操作，请刷新后重试");
    }

    @ExceptionHandler(DataAccessException.class)
    public Object data(Exception e) {
        log.error("数据库或Redis访问异常", e);
        return error(503, "数据服务暂不可用，请根据requestId查看后端日志");
    }

    @ExceptionHandler(Exception.class)
    public Object unknown(Exception e) {
        log.error("未预期的服务异常", e);
        return error(500, "服务处理失败，请根据requestId查看后端日志");
    }
}
