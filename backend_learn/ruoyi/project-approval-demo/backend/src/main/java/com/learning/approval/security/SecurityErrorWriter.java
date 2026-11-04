package com.learning.approval.security;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.learning.approval.common.ApiResponse;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.springframework.stereotype.Component;

/** 过滤器发生在Controller之前，不能依赖ControllerAdvice替它输出异常。 */
@Component
public class SecurityErrorWriter {

    private final ObjectMapper json;

    public SecurityErrorWriter(ObjectMapper json) {
        this.json = json;
    }

    public void write(HttpServletResponse response, int status, String message) throws IOException {
        response.setStatus(status);
        response.setContentType("application/json;charset=UTF-8");
        json.writeValue(response.getWriter(), ApiResponse.error(status, message));
    }
}
