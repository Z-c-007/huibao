package com.ruoyi.system.mapper;

import java.util.List;
import org.apache.ibatis.annotations.Param;
import com.ruoyi.system.domain.ForumTopic;
import com.ruoyi.system.domain.ForumComment;

/** MyBatis 为接口创建代理；namespace + 方法名对应 XML 中的 SQL。 */
public interface ForumMapper
{
    ForumTopic selectDemoTopic();
    ForumTopic selectTopicById(Long topicId);
    ForumComment selectCommentById(Long commentId);
    List<ForumComment> selectComments(Long topicId);
    List<ForumComment> selectReplies(@Param("topicId") Long topicId, @Param("parentId") Long parentId);
    int insertComment(ForumComment comment);
    ForumComment selectCommentForUpdate(Long commentId);
    int updateContent(ForumComment comment);
    int deleteReplies(Long parentId);
    int deleteComment(Long commentId);
}
