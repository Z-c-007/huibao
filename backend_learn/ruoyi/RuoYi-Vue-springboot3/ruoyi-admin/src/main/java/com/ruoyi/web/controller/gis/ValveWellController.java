package com.ruoyi.web.controller.gis;

import java.util.List;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Profile;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import com.ruoyi.common.annotation.Anonymous;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.system.domain.ValveWell;
import com.ruoyi.system.service.IValveWellService;

/**
 * 阀井基础信息查询：汇报时从这个 HTTP 请求入口开始阅读。
 *
 * 完整调用链：浏览器 → Controller → Service → Mapper → XML → MySQL，
 * 然后查询结果逐层返回，由 Spring MVC 配合 Jackson 转换成 JSON。
 *
 * 本示例只在显式启用 valve-well-demo 配置时注册接口，供本地学习使用。
 * 不启用该配置时，不会注册这个免登录接口；请勿在公开服务器启用演示配置。
 */
@Profile("valve-well-demo")
@RestController
@RequestMapping("/gis/valveWell")
public class ValveWellController extends BaseController
{
    // Spring 将业务服务对象注入这里，不需要每次请求都自己 new 一个 Service。
    @Autowired
    private IValveWellService valveWellService;

    /**
     * GET /gis/valveWell/list：查询全部教学数据，不接收筛选或分页参数。
     *
     * Anonymous 是若依已有的注解，使此演示接口可直接通过浏览器访问。
     * 类上的 Profile 限制了它的启用范围，不需要修改全局 SecurityConfig。
     * 此处只适用于少量教学数据，大规模业务台账应增加分页、权限等机制。
     */
    @Anonymous
    @GetMapping("/list")
    public AjaxResult list()
    {
        // 1. 调用 Service，得到 Java 对象列表；这一步会等待数据库查询完成。
        List<ValveWell> list = valveWellService.selectValveWellList();

        // 2. 继承 BaseController 后，可复用 success 方法，包装为 code/msg/data。
        // 3. 返回的是 Java 响应对象；转换成 HTTP JSON 响应由框架完成。
        //    没有记录时 list 是空列表，前端收到 data: []。
        return success(list);
    }
}
