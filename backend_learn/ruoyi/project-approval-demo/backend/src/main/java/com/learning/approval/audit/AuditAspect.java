package com.learning.approval.audit;

import com.learning.approval.domain.AuditLog;
import com.learning.approval.exception.BusinessException;
import com.learning.approval.security.CurrentUser;
import com.learning.approval.service.AuditLogService;
import jakarta.servlet.http.HttpServletRequest;
import org.aspectj.lang.*;
import org.aspectj.lang.annotation.*;
import org.slf4j.*;
import org.springframework.dao.*;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.*;

/** 不记录方法参数或请求体，避免密码、JWT和材料正文进入审计日志。 */
@Aspect
@Component
public class AuditAspect {

    private static final Logger log = LoggerFactory.getLogger(AuditAspect.class);
    private final AuditLogService logs;

    public AuditAspect(AuditLogService logs) {
        this.logs = logs;
    }

    private String cut(String value, int max) {
        return value == null ? null : value.substring(0, Math.min(value.length(), max));
    }

    @Around("@annotation(action)")
    public Object around(ProceedingJoinPoint point, AuditAction action) throws Throwable {
        long started = System.nanoTime();
        boolean success = false;
        int status = 200;
        String message = "成功";
        try {
            Object result = point.proceed();
            success = true;
            return result;
        } catch (Throwable e) {
            status =
                e instanceof BusinessException b
                    ? b.getStatus()
                    : e instanceof AccessDeniedException
                      ? 403
                      : e instanceof DataIntegrityViolationException
                        ? 409
                        : e instanceof DataAccessException
                          ? 503
                          : 500;
            message =
                e instanceof BusinessException
                    ? e.getMessage()
                    : "操作失败：" + e.getClass().getSimpleName();
            throw e;
        } finally {
            try {
                var attributes =
                    (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
                if (attributes != null) {
                    HttpServletRequest request = attributes.getRequest();
                    AuditLog row = new AuditLog();
                    row.setCategory(action.category());
                    row.setOperation(action.value());
                    row.setRequestId(MDC.get("requestId"));
                    row.setHttpMethod(request.getMethod());
                    row.setPath(cut(request.getServletPath(), 255));
                    row.setIp(cut(request.getRemoteAddr(), 64));
                    var authentication = SecurityContextHolder.getContext().getAuthentication();
                    if (
                        authentication != null &&
                        authentication.getPrincipal() instanceof CurrentUser user
                    ) {
                        row.setActorId(user.id());
                        row.setActorName(user.username());
                    } else {
                        row.setActorName(cut((String) request.getAttribute("loginUsername"), 50));
                    }
                    row.setSuccess(success);
                    row.setHttpStatus(status);
                    row.setMessage(cut(message, 500));
                    row.setDurationMillis((System.nanoTime() - started) / 1_000_000);
                    logs.save(row);
                }
            } catch (RuntimeException e) {
                log.error("独立审计日志保存失败，业务结果保持不变", e);
            }
        }
    }
}
