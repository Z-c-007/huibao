package com.ruoyi.system.service.impl;

import java.util.List;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import com.ruoyi.system.domain.ValveWell;
import com.ruoyi.system.mapper.ValveWellMapper;
import com.ruoyi.system.service.IValveWellService;

/**
 * 阀井业务实现层，implements 表示实现 IValveWellService 约定的方法。
 * Service 是放置业务规则、协调数据访问的地方。
 * 本例只是读取全部基础信息，没有额外业务判断，因此直接转交 Mapper。
 */
@Service
public class ValveWellServiceImpl implements IValveWellService
{
    // Mapper 的实际对象由 MyBatis 与 Spring 集成创建、管理，再注入这里。
    @Autowired
    private ValveWellMapper valveWellMapper;

    /**
     * Controller 调用这里，接着进入 Mapper；获得结果后原样返回列表。
     * 本次是单次只读查询，不需要额外添加用于协调多次写入的事务逻辑。
     */
    @Override
    public List<ValveWell> selectValveWellList()
    {
        return valveWellMapper.selectValveWellList();
    }
}
