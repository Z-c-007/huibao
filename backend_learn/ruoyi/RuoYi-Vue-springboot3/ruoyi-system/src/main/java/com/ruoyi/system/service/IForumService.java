package com.ruoyi.system.service;

import java.util.List;
import com.ruoyi.system.domain.ForumTopic;
import com.ruoyi.system.domain.ForumComment;
import com.ruoyi.system.domain.dto.ForumCommentRequest;
import com.ruoyi.system.domain.dto.ForumReplyRequest;

/** Service接口声明业务能力；执行代码在 ForumServiceImpl 中，而不是接口中。 */
public interface IForumService
{
    ForumTopic getDemoTopic();
    ForumTopic requireTopic(Long topicId);
    ForumComment requireRootComment(Long topicId, Long commentId);
    List<ForumComment> selectComments(Long topicId);
    List<ForumComment> selectReplies(Long topicId, Long parentId);
    ForumComment addComment(ForumCommentRequest request);
    ForumComment addReply(ForumReplyRequest request);
    /**
     * 服务契约（方法签名）：约定编辑能力的输入、返回类型；这里不规定必须怎样调用Mapper。
     * 实际业务步骤由 ForumServiceImpl 实现，Controller依赖接口使用这个能力。
     * @param commentId 待编辑记录的编号
     * @param request 所属主题和新内容
     * @param reply false表示顶层评论，true表示维护回复
     * @return 编辑后的评论对象，尚未包装为HTTP响应
     */
    ForumComment updateComment(Long commentId, ForumCommentRequest request, boolean reply);
    void deleteComment(Long commentId, boolean reply);
}

