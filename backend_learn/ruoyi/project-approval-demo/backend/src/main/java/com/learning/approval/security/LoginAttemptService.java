package com.learning.approval.security;

import com.learning.approval.common.HashUtils;
import com.learning.approval.config.SecurityProperties;
import com.learning.approval.exception.BusinessException;
import java.util.List;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Service;

/** Lua将“计数+首次设置TTL”放在一次Redis操作中，避免计数键永不过期。 */
@Service
public class LoginAttemptService {

    private static final DefaultRedisScript<Long> INCREMENT = new DefaultRedisScript<>(
        "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]); end; return n",
        Long.class
    );
    private final StringRedisTemplate redis;
    private final SecurityProperties properties;

    public LoginAttemptService(StringRedisTemplate redis, SecurityProperties properties) {
        this.redis = redis;
        this.properties = properties;
    }

    private String account(String username) {
        return (
            properties.redisPrefix() +
            "login-failures:" +
            HashUtils.sha256(username.toLowerCase(java.util.Locale.ROOT))
        );
    }

    public void check(String username, String ip) {
        Long requests = redis.execute(
            INCREMENT,
            List.of(properties.redisPrefix() + "login-ip:" + HashUtils.sha256(ip)),
            "60"
        );
        BusinessException.require(
            requests != null && requests <= 30,
            429,
            "登录请求过于频繁，请稍后再试"
        );
        String failures = redis.opsForValue().get(account(username));
        if (failures != null && Integer.parseInt(failures) >= properties.maxLoginFailures()) {
            throw new BusinessException(429, "账号登录失败次数过多，请在锁定时间结束后重试");
        }
    }

    public void failed(String username) {
        redis.execute(
            INCREMENT,
            List.of(account(username)),
            Integer.toString(properties.loginLockSeconds())
        );
    }

    public void success(String username) {
        redis.delete(account(username));
    }
}
