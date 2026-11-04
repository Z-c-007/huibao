package com.ruoyi.forum;

import java.util.Set;
import jakarta.validation.Validation;
import jakarta.validation.ValidatorFactory;
import org.hibernate.validator.messageinterpolation.ParameterMessageInterpolator;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import com.ruoyi.common.core.domain.entity.SysUser;
import com.ruoyi.common.core.domain.model.LoginUser;
import com.ruoyi.common.exception.ServiceException;
import com.ruoyi.system.domain.ForumComment;
import com.ruoyi.system.domain.ForumTopic;
import com.ruoyi.system.domain.dto.ForumCommentRequest;
import com.ruoyi.system.domain.dto.ForumReplyRequest;
import com.ruoyi.system.mapper.ForumMapper;
import com.ruoyi.system.service.impl.ForumServiceImpl;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/** 业务规则单测：替换数据库访问，但不把它冒充MySQL联调。 */
@ExtendWith(MockitoExtension.class)
class ForumServiceTest
{
    @Mock private ForumMapper mapper;
    @InjectMocks private ForumServiceImpl service;

    @BeforeEach
    void login()
    {
        SysUser user = new SysUser();
        user.setUserName("forum_member");
        user.setNickName("真实成员");
        LoginUser principal = new LoginUser(123L, 100L, user, Set.of("forum:comment:add"));
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(principal, null));
    }

    @AfterEach
    void clear() { SecurityContextHolder.clearContext(); }

    private void topicExists()
    {
        ForumTopic topic = new ForumTopic(); topic.setTopicId(1L);
        when(mapper.selectTopicById(1L)).thenReturn(topic);
    }

    private ForumCommentRequest request(String content)
    {
        ForumCommentRequest request = new ForumCommentRequest();
        request.setTopicId(1L); request.setContent(content); return request;
    }

    @Test
    void commentUsesServerIdentityAndGeneratedId()
    {
        topicExists();
        when(mapper.insertComment(any())).thenAnswer(call -> {
            ForumComment row = call.getArgument(0); row.setCommentId(99L); return 1;
        });
        ForumComment result = service.addComment(request("  建议增加位置查询  "));
        assertEquals(123L, result.getAuthorId());
        assertEquals("真实成员", result.getAuthorName());
        assertEquals("forum_member", result.getCreateBy());
        assertEquals("建议增加位置查询", result.getContent());
        assertNull(result.getParentId());
        assertNotNull(result.getCreateTime());
        assertEquals(99L, result.getCommentId());
    }

    @Test
    void blankContentNeverWrites()
    {
        topicExists();
        assertThrows(ServiceException.class, () -> service.addComment(request(" \n\t ")));
        verify(mapper, never()).insertComment(any());
    }

    @Test
    void overlongContentNeverWrites()
    {
        topicExists();
        assertThrows(ServiceException.class, () -> service.addComment(request("字".repeat(201))));
        verify(mapper, never()).insertComment(any());
    }

    @Test
    void missingTopicNeverWrites()
    {
        assertThrows(ServiceException.class, () -> service.addComment(request("建议")));
        verify(mapper, never()).insertComment(any());
    }

    @Test
    void missingParentNeverWrites()
    {
        topicExists();
        ForumReplyRequest request = new ForumReplyRequest(); request.setTopicId(1L); request.setParentId(7L); request.setContent("回复");
        assertThrows(ServiceException.class, () -> service.addReply(request));
        verify(mapper, never()).insertComment(any());
    }

    @Test
    void replyCannotCrossTopic()
    {
        topicExists();
        ForumComment parent = new ForumComment(); parent.setTopicId(2L);
        when(mapper.selectCommentById(7L)).thenReturn(parent);
        assertThrows(ServiceException.class, () -> service.requireRootComment(1L, 7L));
    }

    @Test
    void replyCannotTargetAnotherReply()
    {
        topicExists();
        ForumComment parent = new ForumComment(); parent.setTopicId(1L); parent.setParentId(6L);
        when(mapper.selectCommentById(7L)).thenReturn(parent);
        assertThrows(ServiceException.class, () -> service.requireRootComment(1L, 7L));
    }

    @Test
    void validReplyPersistsRootRelationship()
    {
        topicExists();
        ForumComment parent = new ForumComment(); parent.setTopicId(1L);
        when(mapper.selectCommentById(7L)).thenReturn(parent);
        when(mapper.insertComment(any())).thenReturn(1);
        ForumReplyRequest request = new ForumReplyRequest(); request.setTopicId(1L); request.setParentId(7L); request.setContent(" 已记录 ");
        ForumComment result = service.addReply(request);
        assertEquals(7L, result.getParentId());
        assertEquals("已记录", result.getContent());
    }

    private ForumComment managedRow(Long parentId, Long authorId)
    {
        ForumComment row = new ForumComment(); row.setCommentId(7L); row.setTopicId(1L);
        row.setParentId(parentId); row.setAuthorId(authorId); row.setContent("原内容");
        when(mapper.selectCommentForUpdate(7L)).thenReturn(row);
        return row;
    }

    @Test
    void replyEditRejectsAnotherAuthorBeforeWriting()
    {
        managedRow(3L, 999L);
        assertThrows(ServiceException.class, () -> service.updateComment(7L, request("修改"), true));
        verify(mapper, never()).updateContent(any());
    }

    @Test
    void replyDeleteRejectsAnotherAuthorBeforeDeleting()
    {
        managedRow(3L, 999L);
        assertThrows(ServiceException.class, () -> service.deleteComment(7L, true));
        verify(mapper, never()).deleteComment(any());
    }

    @Test
    void cannotBypassReplyOwnershipUsingCommentEndpoint()
    {
        managedRow(3L, 999L);
        assertThrows(ServiceException.class, () -> service.deleteComment(7L, false));
        assertThrows(ServiceException.class, () -> service.updateComment(7L, request("修改"), false));
        verify(mapper, never()).deleteComment(any());
        verify(mapper, never()).updateContent(any());
    }

    @Test
    void ownReplyEditPreservesIdentityAndRelationship()
    {
        ForumComment row = managedRow(3L, 123L);
        when(mapper.updateContent(any())).thenReturn(1);
        assertSame(row, service.updateComment(7L, request(" 修改后的内容 "), true));
        assertEquals("修改后的内容", row.getContent());
        assertEquals(123L, row.getAuthorId()); assertEquals(3L, row.getParentId());
    }

    @Test
    void rootDeletionDeletesChildrenBeforeParent()
    {
        managedRow(null, 999L);
        when(mapper.deleteComment(7L)).thenReturn(1);
        service.deleteComment(7L, false);
        var order = inOrder(mapper);
        order.verify(mapper).selectCommentForUpdate(7L);
        order.verify(mapper).deleteReplies(7L);
        order.verify(mapper).deleteComment(7L);
    }

    @Test
    void ownReplyDeletionDoesNotDeleteSiblingReplies()
    {
        managedRow(3L, 123L);
        when(mapper.deleteComment(7L)).thenReturn(1);
        service.deleteComment(7L, true);
        verify(mapper, never()).deleteReplies(any());
    }

    @Test
    void editRejectsWrongTopicAndBlankText()
    {
        managedRow(null, 999L);
        ForumCommentRequest wrong = request("修改"); wrong.setTopicId(2L);
        assertThrows(ServiceException.class, () -> service.updateComment(7L, wrong, false));
        assertThrows(ServiceException.class, () -> service.updateComment(7L, request(" "), false));
        verify(mapper, never()).updateContent(any());
    }

    @Test
    void validationCoversInheritedReplyFields()
    {
        try (ValidatorFactory factory = Validation.byDefaultProvider().configure()
                .messageInterpolator(new ParameterMessageInterpolator()).buildValidatorFactory())
        {
            ForumReplyRequest request = new ForumReplyRequest(); request.setTopicId(1L); request.setParentId(7L); request.setContent("  ");
            assertFalse(factory.getValidator().validate(request).isEmpty());
            request.setContent("字".repeat(201));
            assertFalse(factory.getValidator().validate(request).isEmpty());
            request.setContent("正常回复");
            assertTrue(factory.getValidator().validate(request).isEmpty());
        }
    }
}
