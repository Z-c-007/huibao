package com.learning.approval.service.impl;

import static com.learning.approval.exception.BusinessException.require;

import com.learning.approval.domain.*;
import com.learning.approval.mapper.*;
import com.learning.approval.service.ApprovalRoutePlanner;
import java.util.*;
import org.springframework.stereotype.Service;

/** 只负责算路径，不保存数据。调用者在同一提交事务中冻结结果。 */
@Service
public class OrganizationApprovalRoutePlanner implements ApprovalRoutePlanner {

    private final UserMapper users;
    private final RoleMapper roles;

    public OrganizationApprovalRoutePlanner(UserMapper users, RoleMapper roles) {
        this.users = users;
        this.roles = roles;
    }

    @Override
    public List<Node> plan(Project project, List<Long> selected) {
        require(
            selected.size() <= 50 && new HashSet<>(selected).size() == selected.size(),
            400,
            "审批人重复或数量过多"
        );
        List<Node> route = new ArrayList<>();
        Set<Long> visited = new HashSet<>();
        Long orgId = project.getOrgId();
        boolean first = true;
        while (orgId != null) {
            require(visited.add(orgId) && visited.size() <= 32, 409, "组织层级存在循环或超过32层");
            Organization organization = users.selectOrganization(orgId);
            require(organization != null, 409, "组织结构不完整，请联系管理员");
            List<AppUser> pool = roles.selectReviewers(orgId, project.getCreatorId());
            if (first) {
                Set<Long> allowed = new HashSet<>();
                pool.forEach(u -> allowed.add(u.getId()));
                require(
                    allowed.containsAll(selected),
                    400,
                    "所选人员须为本单位有效审批人，且不能是填报人本人"
                );
                pool = pool
                    .stream()
                    .filter(u -> selected.contains(u.getId()))
                    .toList();
            }
            if (!pool.isEmpty()) route.add(new Node(organization, List.copyOf(pool)));
            orgId = organization.getParentId();
            first = false;
        }
        require(!route.isEmpty(), 409, "本级与上级组织均无可用审批人，不能提交");
        return route;
    }
}
