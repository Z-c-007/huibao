package com.learning.approval.service;

import com.learning.approval.domain.AuditLog;
import com.learning.approval.mapper.AuditMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.*;

/** 操作失败日志使用独立事务；业务流转记录则在ProjectService业务事务内保存。 */
@Service
public class AuditLogService {

    private final AuditMapper mapper;

    public AuditLogService(AuditMapper mapper) {
        this.mapper = mapper;
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void save(AuditLog log) {
        mapper.insert(log);
    }
}
