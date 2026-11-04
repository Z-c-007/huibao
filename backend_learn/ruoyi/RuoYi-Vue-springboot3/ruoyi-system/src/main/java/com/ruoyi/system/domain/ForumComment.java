package com.ruoyi.system.domain;

import com.ruoyi.common.core.domain.BaseEntity;

/**
 * 评论与一级回复共用的数据对象。parentId 为 null 表示顶层评论，非空表示维护人员回复。
 * 本例没有编辑删除，因此作者昵称保存为发表时的快照，不随账号昵称修改而改变。
 */
public class ForumComment extends BaseEntity
{
    private static final long serialVersionUID = 1L;
    private Long commentId;
    private Long topicId;
    private Long parentId;
    private Long authorId;
    private String authorName;
    private String content;

    public Long getCommentId() { return commentId; }
    public void setCommentId(Long commentId) { this.commentId = commentId; }
    public Long getTopicId() { return topicId; }
    public void setTopicId(Long topicId) { this.topicId = topicId; }
    public Long getParentId() { return parentId; }
    public void setParentId(Long parentId) { this.parentId = parentId; }
    public Long getAuthorId() { return authorId; }
    public void setAuthorId(Long authorId) { this.authorId = authorId; }
    public String getAuthorName() { return authorName; }
    public void setAuthorName(String authorName) { this.authorName = authorName; }
    public String getContent() { return content; }
    public void setContent(String content) { this.content = content; }
}
