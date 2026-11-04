package com.ruoyi.forum;

import java.util.Set;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.core.context.SecurityContextHolder;
import com.ruoyi.common.core.domain.entity.SysUser;
import com.ruoyi.common.core.domain.model.LoginUser;
import com.ruoyi.framework.web.service.PermissionService;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;
import com.ruoyi.system.domain.ForumComment;
import com.ruoyi.system.domain.dto.ForumReplyRequest;
import com.ruoyi.system.service.IForumService;
import com.ruoyi.web.controller.forum.ForumController;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/**
 * 使用真实Spring方法权限代理和若依PermissionService验证拒绝发生在业务调用前。
 * Service为Mock，测试不需要初始化数据库，也不宣称验证了HTTP过滤器或MySQL。
 */
class ForumPermissionTest
{
    private AnnotationConfigApplicationContext context;
    private IForumService service;
    private ForumController controller;

    @Configuration
    @EnableMethodSecurity
    static class Config
    {
        @Bean(name = "ss") PermissionService permissionService() { return new PermissionService(); }
        @Bean IForumService forumService() { return mock(IForumService.class); }
        @Bean ForumController forumController() { return new ForumController(); }
    }

    @BeforeEach
    void setup()
    {
        // 若依PermissionService会把权限标识记入当前请求属性，需要真实的请求上下文。
        RequestContextHolder.setRequestAttributes(new ServletRequestAttributes(new MockHttpServletRequest()));
        context = new AnnotationConfigApplicationContext(Config.class);
        service = context.getBean(IForumService.class);
        controller = context.getBean(ForumController.class);
    }

    @AfterEach
    void close()
    {
        SecurityContextHolder.clearContext();
        RequestContextHolder.resetRequestAttributes();
        context.close();
    }

    private void login(Set<String> permissions)
    {
        SysUser user = new SysUser(); user.setUserName("test");
        LoginUser principal = new LoginUser(123L, 100L, user, permissions);
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(principal, null));
    }

    @Test
    void memberCannotReplyEvenWhenCallingControllerDirectly()
    {
        login(Set.of("forum:topic:query", "forum:comment:list", "forum:comment:add"));
        assertThrows(AccessDeniedException.class, () -> controller.reply(new ForumReplyRequest()));
        verifyNoInteractions(service);
    }

    @Test
    void operatorWithReplyPermissionCanEnterBusiness()
    {
        login(Set.of("forum:reply:add"));
        when(service.addReply(any())).thenReturn(new ForumComment());
        assertEquals(200, controller.reply(new ForumReplyRequest()).get("code"));
        verify(service).addReply(any());
    }

    @Test
    void memberCanComment()
    {
        login(Set.of("forum:comment:add"));
        when(service.addComment(any())).thenReturn(new ForumComment());
        assertEquals(200, controller.comment(new ForumReplyRequest()).get("code"));
    }

    @Test
    void memberCannotEditOrDeleteEvenThroughDirectControllerCalls()
    {
        login(Set.of("forum:comment:add", "forum:comment:list"));
        assertThrows(AccessDeniedException.class, () -> controller.editComment(3L, new ForumReplyRequest()));
        assertThrows(AccessDeniedException.class, () -> controller.editReply(4L, new ForumReplyRequest()));
        assertThrows(AccessDeniedException.class, () -> controller.removeComment(3L));
        assertThrows(AccessDeniedException.class, () -> controller.removeReply(4L));
        verifyNoInteractions(service);
    }

    @Test
    void operatorPermissionsAllowAllFourManagementEndpoints()
    {
        login(Set.of("forum:comment:edit", "forum:comment:remove", "forum:reply:edit", "forum:reply:remove"));
        controller.editComment(3L, new ForumReplyRequest());
        controller.editReply(4L, new ForumReplyRequest());
        controller.removeComment(3L);
        controller.removeReply(4L);
        verify(service).updateComment(eq(3L), any(), eq(false));
        verify(service).updateComment(eq(4L), any(), eq(true));
        verify(service).deleteComment(3L, false);
        verify(service).deleteComment(4L, true);
    }
}
