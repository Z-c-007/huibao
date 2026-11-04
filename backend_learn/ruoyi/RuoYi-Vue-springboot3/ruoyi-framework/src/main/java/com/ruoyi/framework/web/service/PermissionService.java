package com.ruoyi.framework.web.service;

import java.util.Set;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;
import com.ruoyi.common.constant.Constants;
import com.ruoyi.common.core.domain.entity.SysRole;
import com.ruoyi.common.core.domain.model.LoginUser;
import com.ruoyi.common.utils.SecurityUtils;
import com.ruoyi.common.utils.StringUtils;
import com.ruoyi.framework.security.context.PermissionContextHolder;

/**
 * RuoYi首创 自定义权限实现，ss取自SpringSecurity首字母
 * 
 * @author ruoyi
 */
@Service("ss")
public class PermissionService
{
    /**
     * 验证用户是否具备某权限。
     *
     * 学习示例：Controller 使用 @PreAuthorize("@ss.hasPermi('forum:comment:list')")，
     * Spring Security 会调用本方法，传入 permission = "forum:comment:list"。
     * 假设当前登录账号为 forum_member，其 permissions 是以下字符串集合：
     * {"forum:topic:query", "forum:comment:list", "forum:comment:add"}。
     * 这是说明执行过程的示例，不是这里写死的账号或权限；实际数据来自当前登录身份。
     * 方法读取这些数据并返回判断结果，不修改用户原有的权限集合。
     * 
     * @param permission 权限字符串
     * @return 用户是否具备某权限
     */
    public boolean hasPermi(String permission)
    {
        // 第1步：若依 StringUtils.isEmpty 检查字符串是否为 null、空串或去掉首尾空白后为空。
        // 示例输入 "forum:comment:list" → 判断结果 false，所以不进入下面的 if 分支。
        // 判断不会修改 permission；此时它仍为 "forum:comment:list"。
        if (StringUtils.isEmpty(permission))
        {
            // 只有权限名称为空时才执行：直接返回 false 并结束方法，后续代码不再运行。
            // 本例权限名称非空，不会执行这一行。
            return false;
        }

        // 第2步：若依 SecurityUtils 从 Spring Security 的安全上下文中获取当前登录用户。
        // 内部链路：SecurityContextHolder.getContext().getAuthentication().getPrincipal()，
        // 再转换为若依的 LoginUser；不是在这里重新验证密码或查询用户表。
        // 执行后，新变量 loginUser 引用 forum_member 的登录对象，里面包含上述 permissions 集合。
        // permission 仍为 "forum:comment:list"；若获取认证信息失败，工具方法可能直接抛出异常。
        LoginUser loginUser = SecurityUtils.getLoginUser();

        // 第3步：若依 StringUtils.isNull 检查 loginUser == null；本例为 false。
        // loginUser.getPermissions() 是 getter，只读取对象内已有的 Set<String>，不会在这里查询数据库。
        // Spring CollectionUtils.isEmpty 检查这个集合是否为 null 或没有元素；本例有3个元素，为 false。
        // || 表示“或者”并短路：如果左边已为 true，就不会调用右边，避免对 null 用户取权限。
        // 本例 false || false → false，不进入分支；用户对象、权限集合和 permission 均未改变。
        if (StringUtils.isNull(loginUser) || CollectionUtils.isEmpty(loginUser.getPermissions()))
        {
            // 只有用户为空或权限集合为空时才执行：返回 false，表示无法通过本次权限检查。
            // 本例用户存在且权限集合非空，不会执行这一行。
            return false;
        }

        // 第4步：若依把正在检查的权限写到当前请求的属性中，供后续处理（如数据权限切面）读取。
        // 执行后，请求新增/更新属性：PERMISSION_CONTEXT = "forum:comment:list"。
        // 这是记录检查目标，不是给用户授权；loginUser.permissions 仍是原来的3个权限。
        PermissionContextHolder.setContext(permission);

        // 第5步：调用本类下方的 hasPermissions 辅助方法，传入“用户已有的权限集合”和“要求的权限”。
        // 本例：集合包含 "forum:comment:list"，辅助方法返回 true，本方法随即返回 true 并结束。
        // true 交给 @PreAuthorize，由 Spring Security 放行 Controller 方法；不是直接返回给前端的JSON。
        // 若集合既没有目标权限，也没有全部权限标识，则返回 false，由 Spring Security 拒绝方法调用。
        return hasPermissions(loginUser.getPermissions(), permission);
    }

    /**
     * 验证用户是否不具备某权限，与 hasPermi逻辑相反
     *
     * @param permission 权限字符串
     * @return 用户是否不具备某权限
     */
    public boolean lacksPermi(String permission)
    {
        return hasPermi(permission) != true;
    }

    /**
     * 验证用户是否具有以下任意一个权限
     *
     * @param permissions 以 PERMISSION_DELIMITER 为分隔符的权限列表
     * @return 用户是否具有以下任意一个权限
     */
    public boolean hasAnyPermi(String permissions)
    {
        if (StringUtils.isEmpty(permissions))
        {
            return false;
        }
        LoginUser loginUser = SecurityUtils.getLoginUser();
        if (StringUtils.isNull(loginUser) || CollectionUtils.isEmpty(loginUser.getPermissions()))
        {
            return false;
        }
        PermissionContextHolder.setContext(permissions);
        Set<String> authorities = loginUser.getPermissions();
        for (String permission : permissions.split(Constants.PERMISSION_DELIMITER))
        {
            if (permission != null && hasPermissions(authorities, permission))
            {
                return true;
            }
        }
        return false;
    }

    /**
     * 判断用户是否拥有某个角色
     * 
     * @param role 角色字符串
     * @return 用户是否具备某角色
     */
    public boolean hasRole(String role)
    {
        if (StringUtils.isEmpty(role))
        {
            return false;
        }
        LoginUser loginUser = SecurityUtils.getLoginUser();
        if (StringUtils.isNull(loginUser) || CollectionUtils.isEmpty(loginUser.getUser().getRoles()))
        {
            return false;
        }
        for (SysRole sysRole : loginUser.getUser().getRoles())
        {
            String roleKey = sysRole.getRoleKey();
            if (Constants.SUPER_ADMIN.equals(roleKey) || roleKey.equals(StringUtils.trim(role)))
            {
                return true;
            }
        }
        return false;
    }

    /**
     * 验证用户是否不具备某角色，与 isRole逻辑相反。
     *
     * @param role 角色名称
     * @return 用户是否不具备某角色
     */
    public boolean lacksRole(String role)
    {
        return hasRole(role) != true;
    }

    /**
     * 验证用户是否具有以下任意一个角色
     *
     * @param roles 以 ROLE_DELIMITER 为分隔符的角色列表
     * @return 用户是否具有以下任意一个角色
     */
    public boolean hasAnyRoles(String roles)
    {
        if (StringUtils.isEmpty(roles))
        {
            return false;
        }
        LoginUser loginUser = SecurityUtils.getLoginUser();
        if (StringUtils.isNull(loginUser) || CollectionUtils.isEmpty(loginUser.getUser().getRoles()))
        {
            return false;
        }
        for (String role : roles.split(Constants.ROLE_DELIMITER))
        {
            if (hasRole(role))
            {
                return true;
            }
        }
        return false;
    }

    /**
     * 判断是否包含权限
     * 
     * @param permissions 权限列表
     * @param permission 权限字符串
     * @return 用户是否具备某权限
     */
    private boolean hasPermissions(Set<String> permissions, String permission)
    {
        // permissions（复数）是用户已有的权限集合；permission（单数）是接口要求的一项权限。
        // 本例 permissions = {"forum:topic:query", "forum:comment:list", "forum:comment:add"}，
        // permission = "forum:comment:list"。两个参数和原集合在下面的比较中都不会被修改。
        // ① Constants.ALL_PERMISSION 是若依常量 "*:*:*"，Java Set.contains 检查集合是否包含它。
        //    本例不包含 → false；若包含 → true，|| 短路，直接通过，不再计算右边。
        // ② 若依 StringUtils.trim 返回去掉首尾空白的字符串，null 时返回空串；不修改原变量。
        //    本例 trim 后仍为 "forum:comment:list"。
        // ③ permissions.contains("forum:comment:list") → true，因为集合中有完全相同的字符串。
        //    这里不拆分冒号、不做一般性的通配符匹配，"*:*:*" 是前面单独检查的特殊标识。
        // ④ 本例整体结果 false || true → true，返回给 hasPermi；原始账号和权限数据保持不变。
        return permissions.contains(Constants.ALL_PERMISSION) || permissions.contains(StringUtils.trim(permission));
    }
}
