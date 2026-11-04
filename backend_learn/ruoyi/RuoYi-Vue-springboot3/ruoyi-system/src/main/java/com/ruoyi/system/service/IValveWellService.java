package com.ruoyi.system.service;

import java.util.List;
import com.ruoyi.system.domain.ValveWell;

/**
 * 阀井业务服务的 Java 接口，声明服务能够提供什么能力。
 * 这里的 interface 不是浏览器调用的 HTTP 接口，而是 Java 方法的约定。
 * 具体实现位于 impl/ValveWellServiceImpl.java。
 */
public interface IValveWellService
{
    /**
     * 查询全部阀井基础信息，按内部 ID 升序排列。
     * @return 阀井对象列表；没有记录时返回空列表
     */
    List<ValveWell> selectValveWellList();
}
