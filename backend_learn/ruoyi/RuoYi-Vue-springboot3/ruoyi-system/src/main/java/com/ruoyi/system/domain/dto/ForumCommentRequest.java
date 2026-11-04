package com.ruoyi.system.domain.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;

/**
 * 客户端只提交主题ID和内容。作者、角色、创建时间不属于客户端可控制的参数。
 * 不直接接收 ForumComment 实体，避免客户端将 parentId 混入普通评论变成回复。
 */
public class ForumCommentRequest
{
    @NotNull(message = "请选择主题")
    @Positive(message = "主题编号必须为正数")
    private Long topicId;

    @NotBlank(message = "内容不能为空")
    @Size(max = 200, message = "内容不能超过200个字符")
    private String content;

    public Long getTopicId() { return topicId; }
    public void setTopicId(Long topicId) { this.topicId = topicId; }
    public String getContent() { return content; }
    // strip 去除首尾空白，再由 Bean Validation 校验长度和非空。
    public void setContent(String content) { this.content = content == null ? null : content.strip(); }
}
