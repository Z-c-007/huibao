package com.learning.approval.security;

import com.learning.approval.config.SecurityProperties;
import io.jsonwebtoken.*;
import io.jsonwebtoken.io.Decoders;
import io.jsonwebtoken.security.Keys;
import java.time.Instant;
import java.util.Date;
import javax.crypto.SecretKey;
import org.springframework.stereotype.Component;

/** 自己编写的JWT签发/校验服务，密码学由JJWT库完成。Base64解码不是解密。 */
@Component
public class JwtTokenProvider {

    private final SecurityProperties properties;
    private final SecretKey key;

    public JwtTokenProvider(SecurityProperties properties) {
        this.properties = properties;
        byte[] bytes = Decoders.BASE64.decode(properties.secretBase64());
        if (bytes.length < 64) throw new IllegalArgumentException(
            "HS512密钥至少需要64字节，请设置APP_JWT_SECRET"
        );
        if (
            properties.refreshThresholdMinutes() >= properties.sessionIdleMinutes() ||
            properties.sessionIdleMinutes() > properties.tokenMinutes()
        ) {
            throw new IllegalArgumentException(
                "续期阈值须小于Redis空闲时长，且空闲时长不能超过JWT最长有效期"
            );
        }
        key = Keys.hmacShaKeyFor(bytes);
    }

    public String create(LoginSession session) {
        return Jwts.builder()
            .issuer(properties.issuer())
            .subject(Long.toString(session.user().id()))
            .id(session.sessionId())
            .claim("authVersion", session.user().authVersion())
            .issuedAt(Date.from(session.issuedAt()))
            .expiration(Date.from(session.absoluteExpiresAt()))
            .signWith(key, Jwts.SIG.HS512)
            .compact();
    }

    public VerifiedToken verify(String token) {
        Claims claims = Jwts.parser()
            .verifyWith(key)
            .requireIssuer(properties.issuer())
            .build()
            .parseSignedClaims(token)
            .getPayload();
        if (
            claims.getId() == null || claims.getExpiration() == null
        ) throw new IllegalArgumentException("缺少JWT声明");
        Number version = claims.get("authVersion", Number.class);
        if (version == null) throw new IllegalArgumentException("缺少权限版本");
        return new VerifiedToken(
            claims.getId(),
            Long.parseLong(claims.getSubject()),
            version.longValue(),
            claims.getExpiration().toInstant()
        );
    }
}
