package com.ruoyi.system.domain.dto;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

/** 维护人员回复还必须提供被回复的顶层评论ID，继承评论请求的主题与内容校验。 */
public class ForumReplyRequest extends ForumCommentRequest
{
    @NotNull(message = "请选择要回复的评论")
    @Positive(message = "评论编号必须为正数")
    private Long parentId;

    public Long getParentId() { return parentId; }
    public void setParentId(Long parentId) { this.parentId = parentId; }
}
