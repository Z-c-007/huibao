package com.learning.approval.common;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;

/** 摘要用于请求幂等和不暴露账号的Redis键，不用于代替BCrypt密码哈希。 */
public final class HashUtils {

    private HashUtils() {}

    public static String sha256(String text) {
        try {
            return HexFormat.of().formatHex(
                MessageDigest.getInstance("SHA-256").digest(text.getBytes(StandardCharsets.UTF_8))
            );
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("当前JDK不支持SHA-256", e);
        }
    }
}
