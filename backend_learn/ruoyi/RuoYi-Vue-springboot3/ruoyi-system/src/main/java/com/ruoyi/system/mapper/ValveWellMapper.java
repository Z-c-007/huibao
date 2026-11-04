package com.ruoyi.system.mapper;

import java.util.List;
import com.ruoyi.system.domain.ValveWell;

/**
 * 数据访问层：声明数据库查询方法，而不是在这里手写 JDBC 操作。
 * 若依已有的 MapperScan 会扫描本包，MyBatis 创建代理来实现调用。
 * XML 的 namespace 对应本接口全名，select 的 id 对应下面的方法名。
 */
public interface ValveWellMapper
{
    /**
     * 执行 resources/mapper/system/ValveWellMapper.xml 中的同名查询。
     * @return 将数据库行映射得到的阀井对象列表
     */
    List<ValveWell> selectValveWellList();
}
