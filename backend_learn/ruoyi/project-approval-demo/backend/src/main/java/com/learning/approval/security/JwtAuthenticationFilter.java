package com.learning.approval.security;

import com.learning.approval.domain.SecurityStamp;
import com.learning.approval.exception.BusinessException;
import com.learning.approval.mapper.UserMapper;
import io.jsonwebtoken.JwtException;
import jakarta.servlet.*;
import jakarta.servlet.http.*;
import java.io.IOException;
import java.util.Objects;
import org.slf4j.*;
import org.springframework.dao.DataAccessException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * 自行实现的认证过滤器：验JWT签名和exp -> 查Redis会话 -> 核对账号/权限版本 -> 设置安全上下文。
 * JWT正确但Redis会话已删除，也不能访问。功能授权随后由@PreAuthorize完成。
 */
@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger(JwtAuthenticationFilter.class);
    private final JwtTokenProvider jwt;
    private final RedisSessionService sessions;
    private final UserMapper users;
    private final SecurityErrorWriter errors;

    public JwtAuthenticationFilter(
        JwtTokenProvider jwt,
        RedisSessionService sessions,
        UserMapper users,
        SecurityErrorWriter errors
    ) {
        this.jwt = jwt;
        this.sessions = sessions;
        this.users = users;
        this.errors = errors;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return request.getServletPath().equals("/api/auth/login");
    }

    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain chain
    ) throws ServletException, IOException {
        String header = request.getHeader("Authorization");
        if (header != null) {
            try {
                BusinessException.require(
                    header.startsWith("Bearer ") && header.length() <= 4096,
                    401,
                    "登录凭证格式不正确"
                );
                VerifiedToken verified = jwt.verify(header.substring(7));
                LoginSession session = sessions.find(verified.sessionId());
                BusinessException.require(
                    session != null &&
                        session.user().id() == verified.userId() &&
                        session.user().authVersion() == verified.authVersion(),
                    401,
                    "登录会话已失效，请重新登录"
                );
                SecurityStamp stamp = users.selectSecurityStamp(verified.userId());
                if (
                    stamp == null ||
                    !Boolean.TRUE.equals(stamp.getEnabled()) ||
                    stamp.getAuthVersion() != verified.authVersion() ||
                    !Objects.equals(stamp.getOrgId(), session.user().orgId())
                ) {
                    sessions.remove(verified.sessionId());
                    throw new BusinessException(401, "账号状态或权限已经变更，请重新登录");
                }
                sessions.touch(session);
                var authorities = session
                    .user()
                    .permissions()
                    .stream()
                    .map(SimpleGrantedAuthority::new)
                    .toList();
                var authentication = UsernamePasswordAuthenticationToken.authenticated(
                    session.user(),
                    null,
                    authorities
                );
                authentication.setDetails(
                    new WebAuthenticationDetailsSource().buildDetails(request)
                );
                SecurityContextHolder.getContext().setAuthentication(authentication);
                request.setAttribute("loginSessionId", session.sessionId());
            } catch (BusinessException e) {
                errors.write(response, e.getStatus(), e.getMessage());
                return;
            } catch (JwtException | IllegalArgumentException e) {
                errors.write(response, 401, "登录凭证无效或已过期，请重新登录");
                return;
            } catch (DataAccessException e) {
                log.error("认证依赖服务访问失败", e);
                errors.write(response, 503, "登录依赖的数据库或Redis暂不可用");
                return;
            } catch (IllegalStateException e) {
                log.error("会话处理异常", e);
                errors.write(response, 503, "登录会话暂不可用");
                return;
            }
        }
        // 不把业务链放进上面的catch：Controller/Service异常应交由统一异常处理器处理。
        chain.doFilter(request, response);
    }
}
