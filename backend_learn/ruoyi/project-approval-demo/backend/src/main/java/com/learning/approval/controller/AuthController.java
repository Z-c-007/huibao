package com.learning.approval.controller;

import com.learning.approval.audit.AuditAction;
import com.learning.approval.common.ApiResponse;
import com.learning.approval.dto.request.*;
import com.learning.approval.dto.response.*;
import com.learning.approval.security.CurrentUser;
import com.learning.approval.service.IAuthService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

/** HTTP入口只接收/校验参数、调用服务、包装响应，不直接写SQL或操作Redis。 */
@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final IAuthService service;

    public AuthController(IAuthService service) {
        this.service = service;
    }

    @PostMapping("/login")
    @AuditAction(value = "LOGIN", category = "AUTH")
    public ApiResponse<LoginResponse> login(
        @Valid @RequestBody LoginRequest body,
        HttpServletRequest request
    ) {
        request.setAttribute("loginUsername", body.username());
        String agent = request.getHeader("User-Agent");
        if (agent != null && agent.length() > 200) agent = agent.substring(0, 200);
        return ApiResponse.success(service.login(body, request.getRemoteAddr(), agent));
    }

    @GetMapping("/me")
    public ApiResponse<CurrentUser> me(@AuthenticationPrincipal CurrentUser user) {
        return ApiResponse.success(user);
    }

    @PostMapping("/logout")
    @AuditAction(value = "LOGOUT", category = "AUTH")
    public ApiResponse<Boolean> logout(HttpServletRequest request) {
        service.logout((String) request.getAttribute("loginSessionId"));
        return ApiResponse.success(true);
    }

    @GetMapping("/sessions")
    public ApiResponse<List<SessionResponse>> sessions(
        @AuthenticationPrincipal CurrentUser user,
        HttpServletRequest request
    ) {
        return ApiResponse.success(
            service.sessions(user, (String) request.getAttribute("loginSessionId"))
        );
    }

    @DeleteMapping("/sessions/{sessionId}")
    @AuditAction(value = "REVOKE_OWN_SESSION", category = "AUTH")
    public ApiResponse<Boolean> revoke(
        @AuthenticationPrincipal CurrentUser user,
        @PathVariable String sessionId
    ) {
        service.revokeSession(user, sessionId);
        return ApiResponse.success(true);
    }

    @PutMapping("/password")
    @AuditAction(value = "CHANGE_PASSWORD", category = "AUTH")
    public ApiResponse<Boolean> password(
        @AuthenticationPrincipal CurrentUser user,
        @Valid @RequestBody PasswordRequest body
    ) {
        service.changePassword(user, body);
        return ApiResponse.success(true);
    }
}
