package com.learning.approval.security;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.learning.approval.config.SecurityProperties;
import com.learning.approval.exception.BusinessException;
import java.time.*;
import java.util.*;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

/** 会话只存Redis；数据库login_session旧表保留但不再参与登录。 */
@Service
public class RedisSessionService {

    private final StringRedisTemplate redis;
    private final ObjectMapper json;
    private final SecurityProperties properties;

    public RedisSessionService(
        StringRedisTemplate redis,
        ObjectMapper json,
        SecurityProperties properties
    ) {
        this.redis = redis;
        this.json = json;
        this.properties = properties;
    }

    private String key(String id) {
        return properties.redisPrefix() + "session:" + id;
    }

    private String index(long userId) {
        return properties.redisPrefix() + "user-sessions:" + userId;
    }

    public LoginSession create(CurrentUser user, String ip, String userAgent) {
        Instant now = Instant.now();
        LoginSession session = new LoginSession(
            UUID.randomUUID().toString(),
            user,
            now,
            now.plusSeconds(properties.tokenMinutes() * 60L),
            ip,
            userAgent
        );
        try {
            redis
                .opsForValue()
                .set(
                    key(session.sessionId()),
                    json.writeValueAsString(session),
                    Duration.ofMinutes(properties.sessionIdleMinutes())
                );
            redis.opsForSet().add(index(user.id()), session.sessionId());
            redis.expire(index(user.id()), Duration.ofMinutes(properties.tokenMinutes()));
            return session;
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("登录会话序列化失败", e);
        }
    }

    public LoginSession find(String sessionId) {
        String value = redis.opsForValue().get(key(sessionId));
        if (value == null) return null;
        try {
            return json.readValue(value, LoginSession.class);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("登录会话格式异常", e);
        }
    }

    public void touch(LoginSession session) {
        long remaining = Duration.between(Instant.now(), session.absoluteExpiresAt()).toSeconds();
        BusinessException.require(remaining > 0, 401, "登录已到期，请重新登录");
        Long ttl = redis.getExpire(key(session.sessionId()));
        BusinessException.require(ttl != null && ttl >= 0, 401, "登录会话已失效");
        if (ttl <= properties.refreshThresholdMinutes() * 60L) {
            // EXPIRE仅更新已经存在的键。不能用SET续期，否则并发退出后可能重建已删除会话。
            boolean renewed = Boolean.TRUE.equals(
                redis.expire(
                    key(session.sessionId()),
                    Duration.ofSeconds(Math.min(properties.sessionIdleMinutes() * 60L, remaining))
                )
            );
            BusinessException.require(renewed, 401, "登录会话已失效");
        }
    }

    public void remove(String sessionId) {
        LoginSession existing = find(sessionId);
        redis.delete(key(sessionId));
        if (existing != null) redis.opsForSet().remove(index(existing.user().id()), sessionId);
    }

    public List<LoginSession> list(long userId) {
        Set<String> ids = redis.opsForSet().members(index(userId));
        if (ids == null) return List.of();
        List<LoginSession> sessions = new ArrayList<>();
        for (String id : ids) {
            LoginSession session = find(id);
            if (session != null && session.user().id() == userId) sessions.add(session);
            else redis.opsForSet().remove(index(userId), id);
        }
        sessions.sort(Comparator.comparing(LoginSession::issuedAt).reversed());
        return sessions;
    }

    public void revokeAll(long userId) {
        Set<String> ids = redis.opsForSet().members(index(userId));
        if (ids != null) for (String id : ids) redis.delete(key(id));
        redis.delete(index(userId));
    }

    /** 只清理旧权限版本；不误删在数据库提交之后刚刚重新登录的新会话。 */
    public void revokeOlderThan(long userId, long currentVersion) {
        Set<String> ids = redis.opsForSet().members(index(userId));
        if (ids == null) return;
        for (String id : ids) {
            LoginSession session = find(id);
            if (session == null) redis.opsForSet().remove(index(userId), id);
            else if (
                session.user().id() == userId && session.user().authVersion() < currentVersion
            ) remove(id);
        }
    }

    public long ttl(String sessionId) {
        Long value = redis.getExpire(key(sessionId));
        return value == null ? -2 : value;
    }
}
