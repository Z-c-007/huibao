package com.learning.approval.mapper;

import com.learning.approval.domain.AuditLog;
import java.util.List;
import org.apache.ibatis.annotations.Param;

public interface AuditMapper {
    int insert(AuditLog log);
    long count(String category);
    List<AuditLog> select(
        @Param("category") String category,
        @Param("limit") int limit,
        @Param("offset") int offset
    );
}
