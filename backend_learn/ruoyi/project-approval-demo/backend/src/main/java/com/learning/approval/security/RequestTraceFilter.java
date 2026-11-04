package com.learning.approval.security;

import jakarta.servlet.*;
import jakarta.servlet.http.*;
import java.io.IOException;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/** 请求ID贯穿响应、文件日志和审计表，方便由前端错误定位后端日志。 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class RequestTraceFilter extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger(RequestTraceFilter.class);

    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain chain
    ) throws ServletException, IOException {
        String id = UUID.randomUUID().toString();
        long started = System.nanoTime();
        MDC.put("requestId", id);
        response.setHeader("X-Request-Id", id);
        try {
            chain.doFilter(request, response);
        } finally {
            String path = request.getServletPath().replaceAll("[\\r\\n\\t]", "_");
            log.info(
                "{} {} -> {} ({}ms)",
                request.getMethod(),
                path,
                response.getStatus(),
                (System.nanoTime() - started) / 1_000_000
            );
            MDC.remove("requestId");
        }
    }
}
