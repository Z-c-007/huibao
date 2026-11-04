package com.ruoyi.web.controller.forum;

import java.util.List;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Positive;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import com.ruoyi.common.annotation.Log;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.core.page.TableDataInfo;
import com.ruoyi.common.enums.BusinessType;
import com.ruoyi.system.domain.ForumComment;
import com.ruoyi.system.domain.dto.ForumCommentRequest;
import com.ruoyi.system.domain.dto.ForumReplyRequest;
import com.ruoyi.system.service.IForumService;

/**
 * 讨论区HTTP入口：沿用若依登录、方法权限、响应包装与操作日志。
 * 没有 Anonymous，也没有演示Profile：必须使用真实登录token和实际权限。
 */
// Spring：标记本类参与方法级参数校验，检查 @Positive、@Min 等约束。
@Validated
@RestController
@RequestMapping("/forum")
public class ForumController extends BaseController
{
    // Spring：注入 IForumService 对应的业务服务对象。
    // 当前项目的实现类是 ForumServiceImpl；注入只准备对象，不会在这里执行查询。
    @Autowired
    private IForumService forumService;

    @PreAuthorize("@ss.hasPermi('forum:topic:query')")
    @GetMapping("/topic")
    public AjaxResult topic() { return success(forumService.getDemoTopic()); }

    /**
     * 分页查询某个讨论主题下的顶层评论（不包含回复）。
     * 请求示例：GET /forum/comments?topicId=1&pageNum=1&pageSize=10
     *
     * @param topicId 讨论主题编号，必须提供且大于0
     * @param pageNum 页码，默认1，最小为1
     * @param pageSize 每页条数，默认10，范围1～50
     * @return 分页结果：code、msg、rows（当前页数据）、total（符合条件的总条数）
     */
    // Spring Security：执行本方法前检查权限，检查不通过则不执行方法体。
    // 表达式中的 @ss 引用若依 PermissionService 注册的名为 ss 的 Spring 对象，
    // hasPermi 是若依提供的方法；forum:comment:list 是本功能定义的权限标识，不是URL。
    @PreAuthorize("@ss.hasPermi('forum:comment:list')")
    // Spring MVC：处理 GET 请求；与类上的 /forum 拼接为 /forum/comments。
    @GetMapping("/comments")
    public TableDataInfo comments(
            // Spring MVC 的 @RequestParam 接收请求参数，默认必填，并转换为 Long。
            // Jakarta Validation 的 @Positive 要求数值大于0；它本身不负责检查非空或主题存在。
            @RequestParam @Positive Long topicId,
            // 未提供参数或传入空值时使用1；Jakarta Validation 的 @Min(1) 要求页码至少为1。
            @RequestParam(defaultValue = "1") @Min(1) Integer pageNum,
            // 默认每页10条；Jakarta Validation 的 @Min、@Max 限定范围为1～50，包含边界。
            @RequestParam(defaultValue = "10") @Min(1) @Max(50) Integer pageSize)
    {
        // 业务检查：主题编号合法不代表主题存在，不存在时由 Service 抛出业务异常。
        // 此步骤内部也会查询数据库，必须放在启动分页之前，避免提前消耗分页状态。
        forumService.requireTopic(topicId);

        // 继承自若依 BaseController，内部调用 PageUtils，再调用 PageHelper。
        // 它从当前HTTP请求读取分页参数，不是直接读取本方法中的 pageNum、pageSize 变量。
        // 为后续第一个 MyBatis 查询设置分页，让分页作用在下面的评论查询上。
        startPage();

        // 业务服务经由 Mapper 和 XML 中的SQL查询评论，返回当前页的评论对象列表。
        List<ForumComment> rows = forumService.selectComments(topicId);

        // 继承自若依 BaseController：包装当前页数据和总条数，供前端分页组件使用。
        // 例如 rows 只有10条，但 total 可以是83；Spring MVC 随后把返回对象转换为JSON。
        return getDataTable(rows);
    }

    @PreAuthorize("@ss.hasPermi('forum:comment:list')")
    @GetMapping("/comments/{commentId}/replies")
    public TableDataInfo replies(@PathVariable @Positive Long commentId, @RequestParam @Positive Long topicId,
            @RequestParam(defaultValue = "1") @Min(1) Integer pageNum,
            @RequestParam(defaultValue = "10") @Min(1) @Max(50) Integer pageSize)
    {
        forumService.requireRootComment(topicId, commentId);
        startPage();
        List<ForumComment> rows = forumService.selectReplies(topicId, commentId);
        return getDataTable(rows);
    }

    @PreAuthorize("@ss.hasPermi('forum:comment:add')")
    @Log(title = "讨论区评论", businessType = BusinessType.INSERT)
    @PostMapping("/comments")
    public AjaxResult comment(@Validated @RequestBody ForumCommentRequest request)
    {
        return success(forumService.addComment(request));
    }

    /**
     * 编辑一条顶层评论：Controller 负责 HTTP 接入，具体业务检查交给 Service。
     * 示例：PUT /forum/comments/3，请求体为
     * {"topicId":1,"content":"建议支持按阀井编号搜索"}。
     *
     * 类上的 /forum 与方法上的 /comments/{commentId} 共同定义接口路径。
     * 注解不是从上到下依次执行的语句：路由匹配、参数处理、权限和日志分别由框架机制处理。
     * 只有方法权限检查通过，才允许执行下面的方法体；前端隐藏按钮不能代替此检查。
     *
     * @param commentId 从路径取得的评论编号，例如3，@Positive 要求其大于0
     * @param request 从JSON请求体绑定得到的参数对象；@Validated 触发其非空、长度等约束校验
     * @return 统一响应对象；Spring MVC 随后使用消息转换器将它写成JSON响应
     */
    // Spring Security：检查当前用户是否具备编辑评论权限，不负责执行修改SQL。
    @PreAuthorize("@ss.hasPermi('forum:comment:edit')")
    // 若依的日志注解：由日志切面统一记录操作；UPDATE 是操作分类，不会自动生成UPDATE SQL。
    @Log(title = "讨论区评论", businessType = BusinessType.UPDATE)
    // Spring MVC：声明该方法处理PUT请求，不表示用户一定有权限，仍需上面的权限机制检查。
    @PutMapping("/comments/{commentId}")
    public AjaxResult editComment(@PathVariable @Positive Long commentId,
            @Validated @RequestBody ForumCommentRequest request)
    {
        // 这是实际调用业务服务，不是声明方法。IForumService 是服务契约，
        // Spring 注入它的实现对象（当前是 ForumServiceImpl），调用会进入实现方法。
        // commentId=3，request携带主题1与新内容，false表示“顶层评论”，不是“修改失败”。
        // Service完成事务处理后返回ForumComment对象，再由继承的success方法包装code/msg/data。
        return success(forumService.updateComment(commentId, request, false));
    }

    @PreAuthorize("@ss.hasPermi('forum:reply:edit')")
    @Log(title = "讨论区维护回复", businessType = BusinessType.UPDATE)
    @PutMapping("/replies/{commentId}")
    public AjaxResult editReply(@PathVariable @Positive Long commentId,
            @Validated @RequestBody ForumCommentRequest request)
    {
        return success(forumService.updateComment(commentId, request, true));
    }

    @PreAuthorize("@ss.hasPermi('forum:comment:remove')")
    @Log(title = "讨论区评论及其回复", businessType = BusinessType.DELETE)
    @DeleteMapping("/comments/{commentId}")
    public AjaxResult removeComment(@PathVariable @Positive Long commentId)
    {
        forumService.deleteComment(commentId, false);
        return success();
    }

    @PreAuthorize("@ss.hasPermi('forum:reply:remove')")
    @Log(title = "讨论区维护回复", businessType = BusinessType.DELETE)
    @DeleteMapping("/replies/{commentId}")
    public AjaxResult removeReply(@PathVariable @Positive Long commentId)
    {
        forumService.deleteComment(commentId, true);
        return success();
    }

    @PreAuthorize("@ss.hasPermi('forum:reply:add')")
    @Log(title = "讨论区维护回复", businessType = BusinessType.INSERT)
    @PostMapping("/replies")
    public AjaxResult reply(@Validated @RequestBody ForumReplyRequest request)
    {
        return success(forumService.addReply(request));
    }
}
