package com.ruoyi.system.service.impl;

import java.util.Date;
import java.util.List;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import com.ruoyi.common.core.domain.model.LoginUser;
import com.ruoyi.common.exception.ServiceException;
import com.ruoyi.common.utils.SecurityUtils;
import com.ruoyi.system.domain.ForumTopic;
import com.ruoyi.system.domain.ForumComment;
import com.ruoyi.system.domain.dto.ForumCommentRequest;
import com.ruoyi.system.domain.dto.ForumReplyRequest;
import com.ruoyi.system.mapper.ForumMapper;
import com.ruoyi.system.service.IForumService;

/**
 * 业务实现：检查目标是否存在、回复层级和主题归属，并从安全上下文取得真实作者。
 * 功能权限由 Controller 的方法权限注解检查，不能靠前端隐藏按钮替代。
 * 删除顶层评论时先删回复再删原评论，使用事务保证一起成功或回滚。
 */
@Service
public class ForumServiceImpl implements IForumService
{
    @Autowired
    private ForumMapper forumMapper;

    @Override
    public ForumTopic getDemoTopic()
    {
        ForumTopic topic = forumMapper.selectDemoTopic();
        if (topic == null) { throw new ServiceException("演示主题不存在，请先执行论坛初始化脚本"); }
        return topic;
    }

    /**
     * 要求指定主题必须存在：先验证编号，再查询数据库；存在则返回主题，不存在则抛出业务异常。
     * 这里查询的是主题，不是评论，也不修改数据库记录。
     *
     * 学习示例：GET /forum/comments?topicId=1&pageNum=1&pageSize=10，
     * Controller 接收 topicId = 1L，再调用 forumService.requireTopic(topicId)。
     * 假设数据库中主题1的标题为“阀井台账系统使用反馈”；编号和数据仅用于说明过程。
     * IForumService 只声明方法签名，这个实现类提供下面的实际处理步骤。
     *
     * @param topicId 主题编号，例如1；在本方法中不会被修改
     * @return 数据库记录映射得到的 ForumTopic 对象，此时是Java对象，还不是JSON
     * @throws ServiceException 编号无效或主题不存在时抛出，中断正常执行流程
     */
    // Java 自带的 @Override：告诉编译器，本方法实现了 IForumService 中声明的方法。
    // 若方法名、参数等不符合重写/实现要求，编译器会报错；它不负责调用方法或查询数据库。
    @Override
    public ForumTopic requireTopic(Long topicId)
    {
        // 第1步：检查输入是否为空或不大于0；|| 左侧为true时，不再计算右侧，避免null参与数值比较。
        // 本例 topicId = 1L：false || false → false，不抛异常，继续执行；topicId 仍为1。
        // 若传入 null、0或负数，则抛出“主题编号无效”，方法中断，不会执行下面的数据库查询。
        // 即使Controller已有 @Positive，这里仍保留业务入口保护，方便其他代码直接调用本方法。
        if (topicId == null || topicId <= 0) { throw new ServiceException("主题编号无效"); }

        // 第2步：调用 Mapper.selectTopicById(1L)，MyBatis 找到 ForumMapper.xml 中同名 select。
        // SQL：SELECT topic_id, title, description, create_time FROM biz_forum_topic WHERE topic_id = #{topicId}。
        // #{topicId} 绑定数值1，而非直接拼接字符串；本次只查主题，不查评论。
        // 假设查询到一行：topic_id=1，title="阀井台账系统使用反馈"，以及描述和创建时间。
        // TopicResult 把 topic_id → topicId、create_time → createTime 等字段映射成 ForumTopic 对象。
        // 执行后 topic 引用这个主题对象，topicId 仍为1；如果没查到记录，topic 为null。
        // 数据库连接失败或SQL执行失败会抛出相应异常，不等同于“没有查到记录”。
        ForumTopic topic = forumMapper.selectTopicById(topicId);

        // 第3步：判断查询结果是否为空。本例找到主题对象，topic == null → false，继续执行。
        // 反例：topicId=99999且数据库没有该主题 → topic=null → 抛出“主题不存在”。
        // 异常向上传递给调用方和项目异常处理机制；Controller 不会继续启动分页、查询评论。
        if (topic == null) { throw new ServiceException("主题不存在"); }

        // 第4步：把主题对象返回给调用方；没有修改输入编号或数据库中的主题。
        // 当前Controller只写 forumService.requireTopic(topicId)，没有变量接收返回对象，
        // 因为这里只需要确认“检查成功且没有异常”，之后继续 startPage() 和评论查询即可。
        // 区分业务情况：主题不存在应报错；主题存在但没有评论，后续可以正常返回空评论列表。
        return topic;
    }

    @Override
    public ForumComment requireRootComment(Long topicId, Long commentId)
    {
        // 检查主题是否存在，如果不存在就抛出异常，后面的逻辑都不会走
        requireTopic(topicId);
        if (commentId == null || commentId <= 0) { throw new ServiceException("评论编号无效"); }
        ForumComment parent = forumMapper.selectCommentById(commentId);
        if (parent == null) { throw new ServiceException("评论不存在"); }
        if (!topicId.equals(parent.getTopicId())) { throw new ServiceException("评论不属于当前主题"); }
        if (parent.getParentId() != null) { throw new ServiceException("只能回复顶层评论，不能回复另一条回复"); }
        return parent;
    }

    // 分页前的存在性检查由 Controller 调用上面的方法完成。
    // PageHelper 拦截的是后续查询，不能让前置检查 SQL 意外消耗分页状态。
    @Override
    public List<ForumComment> selectComments(Long topicId) { return forumMapper.selectComments(topicId); }

    @Override
    public List<ForumComment> selectReplies(Long topicId, Long parentId) { return forumMapper.selectReplies(topicId, parentId); }

    @Override
    public ForumComment addComment(ForumCommentRequest request)
    {
        requireTopic(request.getTopicId());
        // 普通评论的 parentId 固定为 null，不从客户端读取，防止绕过回复接口。
        return save(request, null);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public ForumComment addReply(ForumReplyRequest request)
    {
        // 与删除原评论使用同一把数据库行锁；事务结束后释放。
        forumMapper.selectCommentForUpdate(request.getParentId());
        requireRootComment(request.getTopicId(), request.getParentId());
        return save(request, request.getParentId());
    }

    /**
     * 编辑内容的业务实现：查询并锁定目标、检查业务条件、修改内容、执行UPDATE，再返回对象。
     * 功能权限由Controller的 @PreAuthorize 检查；维护回复还需检查是否属于当前作者。
     *
     * 学习示例（编号及内容仅为说明，不假设数据库必有此记录）：
     * PUT /forum/comments/3，请求体 {"topicId":1,"content":"建议支持按阀井编号搜索"}。
     * 假设原记录：commentId=3，topicId=1，parentId=null，content="建议增加搜索"。
     * 本方法收到：commentId=3L，request携带主题1与新内容，reply=false。
     *
     * @param commentId 待编辑记录编号
     * @param request 编辑参数，包含主题编号和新内容；作者信息不由客户端控制
     * @param reply false表示顶层评论；true表示维护回复，用于区分接口允许操作的记录类型
     * @return 编辑后的ForumComment对象；交给Controller包装，再由框架序列化为JSON
     * @throws ServiceException 记录不存在、类型或主题不匹配、回复不属于本人、内容非法或更新失败
     */
    // Java 的 @Override：表明本方法实现了接口中的方法，并让编译器检查是否符合实现约定。
    // 它不负责路由、依赖注入或数据库访问；这些与本注解是不同机制。
    @Override
    // Spring 声明式事务：本场景从Controller经Spring管理的服务对象调用，事务拦截器负责事务边界。
    // rollbackFor=Exception.class：Exception及其子类异常向外传播时按规则回滚；并非“事务锁”注解。
    // 方法正常完成后提交；提交本身也可能失败，不能把执行到return等同于已成功提交。
    // 实际行锁由requireManageable内部的SELECT ... FOR UPDATE取得，持续到事务提交或回滚。
    @Transactional(rollbackFor = Exception.class)
    public ForumComment updateComment(Long commentId, ForumCommentRequest request, boolean reply)
    {
        // 第1步：按编号查询、加锁并检查目标是否可操作，具体过程见下面的requireManageable。
        // 本例得到target：编号3、主题1、顶层评论、旧内容“建议增加搜索”。此时数据库还没被修改。
        ForumComment target = requireManageable(commentId, reply);

        // 第2步：确认URL指定的记录属于请求体中的主题，防止拿主题1的参数修改主题2的记录。
        // 本例1.equals(1)为true，取反为false，继续；不匹配则抛异常，中断后续更新并回滚事务。
        if (!target.getTopicId().equals(request.getTopicId()))
        {
            throw new ServiceException("评论不属于当前主题");
        }
        // 第3步：读取新内容，null转为空字符串，否则strip去掉首尾空白。
        // 本例content="建议支持按阀井编号搜索"；这是Java中的局部变量，不是数据库更新。
        String content = request.getContent() == null ? "" : request.getContent().strip();
        // 业务入口保留基本校验，不能只依赖前端；Controller中的参数校验也不会代替主题/所有权检查。
        if (content.isBlank()) { throw new ServiceException("内容不能为空"); }
        if (content.length() > 200) { throw new ServiceException("内容不能超过200个字符"); }

        // 第4步：若新旧内容相同，直接返回原对象，不执行UPDATE。
        // 某些数据库连接配置下“值未改变”的影响行数可能为0，提前返回可避免被误判成更新失败。
        if (content.equals(target.getContent())) { return target; }

        // 第5步：只修改Java对象的content属性；作者、主题、父评论等属性保持原值。
        // 此刻target.content已是新内容，但仅调用setter不会自动把变化写入数据库。
        target.setContent(content);

        // 第6步：真正请求更新数据库。MyBatis通过ForumMapper接口与XML的namespace/id找到updateContent。
        // SQL：UPDATE biz_forum_comment SET content = #{content} WHERE comment_id = #{commentId}。
        // 参数取自target：content是新内容，commentId=3；返回int表示影响行数，不是评论编号。
        // 本例预期影响1行；SQL异常会向外传播，影响行数不是1则主动抛业务异常，事务按规则回滚。
        if (forumMapper.updateContent(target) != 1) { throw new ServiceException("修改失败，请刷新后重试"); }

        // 第7步：返回编辑后的Java对象。退出实际方法后，Spring事务拦截器先完成提交，
        // Controller才能取得这次成功调用的返回值，再执行success(...)响应包装。
        // 事务回滚撤销的是本事务内未提交的数据库变更，不会自动把Java对象属性恢复成旧值。
        return target;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteComment(Long commentId, boolean reply)
    {
        requireManageable(commentId, reply);
        // 自引用外键要求先删子记录。删回复和删原评论位于同一个数据库事务中。
        // 若删回复成功后，删除原评论抛异常或影响行数不为1并抛异常，异常向外传播会触发回滚，
        // 此事务内刚删除的回复也随之恢复，不会只永久保留其中一条SQL的删除结果。
        // 这不是“恢复上一次HTTP操作”，也不回滚已提交的其他请求或独立记录的操作日志。
        if (!reply) { forumMapper.deleteReplies(commentId); }
        if (forumMapper.deleteComment(commentId) != 1) { throw new ServiceException("删除失败，请刷新后重试"); }
    }

    /**
     * 编辑/删除前的目标检查：返回可操作的记录对象，失败则抛异常，调用方不再继续写入。
     * 本方法不是权限字符串检查；功能权限在Controller，记录类型与回复作者归属在这里检查。
     *
     * 示例A：commentId=3，reply=false，数据库记录parentId=null，即编辑顶层评论。
     * 示例B：commentId=4，reply=true，数据库记录parentId=3，即编辑评论3下的维护回复4。
     *
     * 本方法由外层已有 @Transactional 的编辑/删除方法调用，因此加锁查询参与同一事务。
     * 查询结果是Java对象；此处不修改评论内容，也不执行UPDATE或DELETE。
     */
    private ForumComment requireManageable(Long commentId, boolean reply)
    {
        // 1. 检查编号，null、0或负数均不允许；例如3是有效编号，继续执行。
        if (commentId == null || commentId <= 0) { throw new ServiceException("评论编号无效"); }

        // 2. 调用MyBatis执行XML中的SELECT ... WHERE comment_id = #{commentId} FOR UPDATE。
        // 对已存在记录，本例按主键定位并取得排他行锁，同时把记录映射成ForumComment对象。
        // 其他事务对同一记录的冲突写入/加锁读取需要等待等处理；普通快照查询不一定被阻塞。
        // 锁由数据库管理，在外层事务结束时释放，不是在本private方法return时就释放。
        ForumComment target = forumMapper.selectCommentForUpdate(commentId);

        // 3. 找不到记录就中断。有效的数字编号并不代表数据库中一定存在该记录。
        if (target == null) { throw new ServiceException("评论不存在或已被删除"); }

        // 4. 核对“接口要操作的类型”与“数据库记录的实际类型”。
        // parentId=null代表顶层评论，parentId!=null代表维护回复。
        // 示例A：false != false → false，通过；示例B：true != true → false，通过。
        // 如果把回复4的编号传给顶层评论接口：false != true → true，抛异常，防止换接口绕过规则。
        if (reply != (target.getParentId() != null)) { throw new ServiceException("操作对象类型不匹配"); }

        // 5. 仅当reply=true时，再要求“当前登录用户ID == 回复作者ID”。
        // 示例B：当前用户101，target.authorId=101 → 通过；若作者是102 → 抛异常。
        // reply=false时因&&短路不执行作者比较：当前业务允许有管理权限的用户管理顶层评论，
        // 但维护人员只能编辑/删除自己的维护回复，不能将两条规则混成“所有记录都仅本人可改”。
        if (reply && !SecurityUtils.getUserId().equals(target.getAuthorId()))
        {
            throw new ServiceException("只能编辑或删除自己的维护回复");
        }
        // 6. 返回已检查的目标对象给updateComment/deleteComment，继续各自的后续业务。
        return target;
    }

    private ForumComment save(ForumCommentRequest request, Long parentId)
    {
        // 即使将来从其他服务调用，也保留关键业务输入约束；不是只依赖页面校验。
        String content = request.getContent() == null ? "" : request.getContent().strip();
        if (content.isBlank()) { throw new ServiceException("内容不能为空"); }
        if (content.length() > 200) { throw new ServiceException("内容不能超过200个字符"); }

        LoginUser loginUser = SecurityUtils.getLoginUser();
        ForumComment comment = new ForumComment();
        comment.setTopicId(request.getTopicId());
        comment.setParentId(parentId);
        comment.setContent(content);
        comment.setAuthorId(loginUser.getUserId());
        comment.setAuthorName(loginUser.getUser().getNickName());
        comment.setCreateBy(loginUser.getUsername());
        comment.setCreateTime(new Date());
        if (forumMapper.insertComment(comment) != 1) { throw new ServiceException("提交失败，请稍后重试"); }
        // XML 回填数据库生成的主键；返回的作者和时间也是服务端真实值。
        return comment;
    }
}
