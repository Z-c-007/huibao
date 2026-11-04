package com.ruoyi.system.domain;

import com.ruoyi.common.core.domain.BaseEntity;

/** 讨论主题的数据对象：一行数据库记录对应一个对象，不负责执行 SQL。 */
public class ForumTopic extends BaseEntity
{
    private static final long serialVersionUID = 1L;
    private Long topicId;
    private String title;
    private String description;

    public Long getTopicId() { return topicId; }
    public void setTopicId(Long topicId) { this.topicId = topicId; }
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
}
