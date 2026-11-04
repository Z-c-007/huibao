package com.learning.approval.security;

import com.learning.approval.mapper.UserMapper;
import org.slf4j.*;
import org.springframework.stereotype.Component;
import org.springframework.transaction.event.*;

/** 权限版本与数据库更新同事务；提交后尽力清理Redis，失败时版本校验仍拒绝旧Token。 */
@Component
public class SessionRevocationListener {

    private static final Logger log = LoggerFactory.getLogger(SessionRevocationListener.class);
    private final RedisSessionService sessions;
    private final UserMapper users;

    public SessionRevocationListener(RedisSessionService sessions, UserMapper users) {
        this.sessions = sessions;
        this.users = users;
    }

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void revoke(SessionRevocationEvent event) {
        for (Long userId : event.userIds()) {
            try {
                var stamp = users.selectSecurityStamp(userId);
                if (stamp == null) sessions.revokeAll(userId);
                else sessions.revokeOlderThan(userId, stamp.getAuthVersion());
            } catch (RuntimeException e) {
                log.warn("用户{}的缓存清理失败，已由数据库权限版本阻止旧会话", userId, e);
            }
        }
    }
}
