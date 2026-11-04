package com.learning.approval.service.impl;

import com.learning.approval.config.SecurityProperties;
import com.learning.approval.domain.AppUser;
import com.learning.approval.dto.request.*;
import com.learning.approval.dto.response.*;
import com.learning.approval.exception.BusinessException;
import com.learning.approval.mapper.*;
import com.learning.approval.security.*;
import com.learning.approval.service.IAuthService;
import java.nio.charset.StandardCharsets;
import java.util.List;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AuthServiceImpl implements IAuthService {

    private final UserMapper users;
    private final RoleMapper roles;
    private final PasswordEncoder passwords;
    private final LoginAttemptService attempts;
    private final RedisSessionService sessions;
    private final JwtTokenProvider jwt;
    private final SecurityProperties properties;
    private final ApplicationEventPublisher events;
    private final String dummyHash;

    public AuthServiceImpl(
        UserMapper users,
        RoleMapper roles,
        PasswordEncoder passwords,
        LoginAttemptService attempts,
        RedisSessionService sessions,
        JwtTokenProvider jwt,
        SecurityProperties properties,
        ApplicationEventPublisher events
    ) {
        this.users = users;
        this.roles = roles;
        this.passwords = passwords;
        this.attempts = attempts;
        this.sessions = sessions;
        this.jwt = jwt;
        this.properties = properties;
        this.events = events;
        dummyHash = passwords.encode("unavailable-account-dummy-password");
    }

    @Override
    public LoginResponse login(LoginRequest request, String ip, String userAgent) {
        String username = request.username().strip();
        attempts.check(username, ip);
        AppUser user = users.selectByUsername(username);
        String hash = user == null ? dummyHash : user.getPasswordHash();
        boolean matched = false;
        if (request.password().getBytes(StandardCharsets.UTF_8).length <= 72) {
            try {
                matched = passwords.matches(request.password(), hash);
            } catch (IllegalArgumentException ignored) {
                /* 损坏的哈希按认证失败处理，不泄露细节。 */
            }
        }
        if (user == null || !matched || !Boolean.TRUE.equals(user.getEnabled())) {
            attempts.failed(username);
            throw new BusinessException(401, "账号或密码错误，或账号已停用");
        }
        CurrentUser current = new CurrentUser(
            user.getId(),
            user.getUsername(),
            user.getDisplayName(),
            user.getOrgId(),
            user.getOrgName(),
            List.copyOf(roles.selectUserRoles(user.getId())),
            List.copyOf(roles.selectUserPermissions(user.getId())),
            user.getAuthVersion()
        );
        LoginSession session = sessions.create(current, ip, userAgent);
        attempts.success(username);
        return new LoginResponse(
            jwt.create(session),
            "Bearer",
            properties.tokenMinutes() * 60L,
            current
        );
    }

    @Override
    public void logout(String sessionId) {
        sessions.remove(sessionId);
    }

    @Override
    public List<SessionResponse> sessions(CurrentUser user, String currentSessionId) {
        return sessions
            .list(user.id())
            .stream()
            .filter(s -> s.user().authVersion() == user.authVersion())
            .map(s ->
                new SessionResponse(
                    s.sessionId(),
                    s.ip(),
                    s.userAgent(),
                    s.issuedAt(),
                    s.absoluteExpiresAt(),
                    sessions.ttl(s.sessionId()),
                    s.sessionId().equals(currentSessionId)
                )
            )
            .toList();
    }

    @Override
    public void revokeSession(CurrentUser user, String sessionId) {
        LoginSession existing = sessions.find(sessionId);
        BusinessException.require(
            existing != null && existing.user().id() == user.id(),
            404,
            "登录会话不存在"
        );
        sessions.remove(sessionId);
    }

    @Override
    @Transactional
    public void changePassword(CurrentUser user, PasswordRequest request) {
        users.lockSecurityStamp(user.id());
        AppUser stored = users.selectById(user.id());
        BusinessException.require(
            request.oldPassword().getBytes(StandardCharsets.UTF_8).length <= 72,
            400,
            "原密码不正确"
        );
        BusinessException.require(
            passwords.matches(request.oldPassword(), stored.getPasswordHash()),
            400,
            "原密码不正确"
        );
        validateNewPassword(request.newPassword());
        BusinessException.require(
            !passwords.matches(request.newPassword(), stored.getPasswordHash()),
            400,
            "新密码不能与原密码相同"
        );
        users.updatePassword(user.id(), passwords.encode(request.newPassword()));
        users.incrementAuthVersion(user.id());
        events.publishEvent(new SessionRevocationEvent(List.of(user.id())));
    }

    public static void validateNewPassword(String password) {
        BusinessException.require(
            password.getBytes(StandardCharsets.UTF_8).length <= 72 &&
                password.matches("(?s)(?=.*[A-Za-z])(?=.*[0-9]).{12,64}"),
            400,
            "密码须为12至64位、包含字母与数字，UTF-8不超过72字节"
        );
    }
}
