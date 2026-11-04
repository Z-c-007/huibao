package com.learning.approval.service.impl;

import static com.learning.approval.exception.BusinessException.require;

import com.learning.approval.common.*;
import com.learning.approval.domain.*;
import com.learning.approval.dto.request.*;
import com.learning.approval.dto.response.*;
import com.learning.approval.mapper.*;
import com.learning.approval.security.CurrentUser;
import com.learning.approval.service.*;
import java.time.*;
import java.util.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.*;

/**
 * 业务层只组织规则和事务，不写SQL，不解析JWT，也不直接操作Redis。
 * 功能权限由Controller的@PreAuthorize校验；这里负责归属、状态、版本、候选资格。
 */
@Service
public class ProjectServiceImpl implements IProjectService {

    private final ProjectMapper projects;
    private final WorkflowMapper workflow;
    private final UserMapper users;
    private final RoleMapper roles;
    private final ApprovalRoutePlanner planner;

    public ProjectServiceImpl(
        ProjectMapper projects,
        WorkflowMapper workflow,
        UserMapper users,
        RoleMapper roles,
        ApprovalRoutePlanner planner
    ) {
        this.projects = projects;
        this.workflow = workflow;
        this.users = users;
        this.roles = roles;
        this.planner = planner;
    }

    private void page(int page, int size) {
        require(page >= 1 && page <= 100000 && size >= 1 && size <= 50, 400, "分页参数不合法");
    }

    private Project locked(String id) {
        Project project = projects.selectForUpdate(id);
        require(project != null, 404, "材料不存在");
        return project;
    }

    private void owner(CurrentUser user, Project project) {
        require(project.getCreatorId() == user.id(), 403, "只能操作本人填报的材料");
    }

    private void version(Project project, long expected) {
        require(project.getVersion() == expected, 409, "材料已变化，请刷新后重新操作");
    }

    private void changed(int count) {
        require(count == 1, 409, "数据已变化，请刷新后重新操作");
    }

    private boolean editable(Project project) {
        return Set.of("DRAFT", "REJECTED").contains(project.getStatus());
    }

    @Override
    @Transactional(readOnly = true, isolation = Isolation.REPEATABLE_READ)
    public PageResult<ProjectView> mine(CurrentUser user, int page, int size, String status) {
        page(page, size);
        return new PageResult<>(
            projects.selectMine(user.id(), status, size, (page - 1) * size),
            projects.countMine(user.id(), status),
            page,
            size
        );
    }

    @Override
    @Transactional(readOnly = true, isolation = Isolation.REPEATABLE_READ)
    public PageResult<ProjectView> tasks(
        CurrentUser user,
        int page,
        int size,
        String status,
        String taskState
    ) {
        page(page, size);
        require(Set.of("PENDING", "PROCESSED").contains(taskState), 400, "任务类型不合法");
        return new PageResult<>(
            projects.selectTasks(user.id(), taskState, status, size, (page - 1) * size),
            projects.countTasks(user.id(), taskState, status),
            page,
            size
        );
    }

    @Override
    public List<ReviewerResponse> reviewers(CurrentUser user, String projectId) {
        long orgId = user.orgId();
        if (projectId != null && !projectId.isBlank()) {
            Project project = projects.selectDetail(projectId);
            require(project != null, 404, "材料不存在");
            owner(user, project);
            orgId = project.getOrgId();
        }
        return roles
            .selectReviewers(orgId, user.id())
            .stream()
            .map(u ->
                new ReviewerResponse(
                    u.getId(),
                    u.getUsername(),
                    u.getDisplayName(),
                    u.getOrgId(),
                    u.getOrgName()
                )
            )
            .toList();
    }

    @Override
    @Transactional(readOnly = true, isolation = Isolation.REPEATABLE_READ)
    public ProjectDetailResponse detail(
        CurrentUser user,
        String projectId,
        Integer requestedRound
    ) {
        ProjectView project = projects.selectDetail(projectId);
        require(project != null, 404, "材料不存在");
        boolean owns =
            project.getCreatorId() == user.id() && user.hasPermission("approval:report:query");
        int currentRound = project.getRoundNo();
        Integer round = null;
        Submission submission = null;
        if (!owns) {
            require(user.hasPermission("approval:review:query"), 403, "没有材料查看权限");
            round = requestedRound == null ? currentRound : requestedRound;
            submission = workflow.selectSubmission(projectId, round);
            require(
                submission != null && workflow.hasReached(projectId, round, user.id()),
                403,
                "该轮材料尚未流转给你"
            );
        }
        Submission current = workflow.selectSubmission(projectId, currentRound);
        boolean canReview =
            user.hasPermission("approval:review:audit") &&
            project.getCreatorId() != user.id() &&
            "PENDING".equals(project.getStatus()) &&
            (round == null || round == currentRound) &&
            current != null &&
            Boolean.TRUE.equals(current.getSnapshotAvailable()) &&
            project.getCurrentStepId() != null &&
            workflow.isPending(project.getCurrentStepId(), user.id());
        if (canReview) canReview =
            workflow.selectStep(project.getCurrentStepId()).getOrgId() == user.orgId();
        String notice = "";
        if (!owns) {
            // 审核人始终看自己获分配轮次的快照，不能看到后续重提或未提交的修改。
            project.setProjectCode(submission.getProjectCode());
            project.setProjectName(submission.getProjectName());
            project.setAmount(submission.getAmount());
            project.setMaterial(submission.getMaterial());
            project.setOrgId(submission.getOrgId());
            project.setOrgName(submission.getOrgName());
            project.setCreatorName(submission.getSubmitterName());
            project.setStatus(submission.getStatus());
            project.setRoundNo(round);
            project.setVisibleRoundNo(round);
            if (round != currentRound) {
                project.setCurrentStepId(null);
                project.setCurrentOrgName(null);
            }
            if (!Boolean.TRUE.equals(submission.getSnapshotAvailable())) {
                project.setProjectName("升级前材料（未保存快照）");
                notice =
                    "此轮在V1提交，没有真实材料快照。仅展示审批轨迹；在审材料请填报人撤回后重新提交。";
            }
        } else if (
            current != null &&
            !Boolean.TRUE.equals(current.getSnapshotAvailable()) &&
            "PENDING".equals(project.getStatus())
        ) {
            notice = "此轮为V1历史数据，尚无材料快照。请撤回并重新提交后再审批。";
        }
        return new ProjectDetailResponse(
            project,
            owns ? workflow.selectSubmissions(projectId) : List.of(submission),
            workflow.selectSteps(projectId, round),
            workflow.selectAssignees(projectId, round),
            workflow.selectEvents(projectId, round),
            owns && editable(project) && user.hasPermission("approval:report:edit"),
            owns &&
                "DRAFT".equals(project.getStatus()) &&
                currentRound == 0 &&
                user.hasPermission("approval:report:delete"),
            owns && editable(project) && user.hasPermission("approval:report:submit"),
            canReview,
            owns &&
                "PENDING".equals(project.getStatus()) &&
                user.hasPermission("approval:report:withdraw"),
            notice
        );
    }

    private void content(Project project, ProjectSaveRequest request) {
        project.setProjectCode(request.code().strip().toUpperCase(Locale.ROOT));
        project.setProjectName(request.name().strip());
        project.setAmount(request.amount());
        project.setMaterial(request.material().strip());
    }

    @Override
    @Transactional
    public ProjectView create(CurrentUser user, ProjectSaveRequest request) {
        require(request.version() == 0, 400, "新材料的版本必须为0");
        Project project = new Project();
        project.setId(UUID.randomUUID().toString());
        content(project, request);
        project.setCreatorId(user.id());
        project.setOrgId(user.orgId());
        project.setStatus("DRAFT");
        project.setVersion(0L);
        project.setRoundNo(0);
        changed(projects.insert(project));
        record(project, user, null, null, "CREATE", null, "DRAFT", null, 0L, "创建材料");
        return projects.selectDetail(project.getId());
    }

    @Override
    @Transactional
    public ProjectView update(CurrentUser user, String projectId, ProjectSaveRequest request) {
        Project project = locked(projectId);
        owner(user, project);
        version(project, request.version());
        require(editable(project), 409, "仅草稿和驳回材料允许编辑");
        content(project, request);
        changed(projects.updateContent(project));
        record(
            project,
            user,
            null,
            null,
            "UPDATE",
            project.getStatus(),
            project.getStatus(),
            project.getVersion(),
            project.getVersion() + 1,
            "修改材料"
        );
        return projects.selectDetail(projectId);
    }

    @Override
    @Transactional
    public SubmissionResponse submit(
        CurrentUser user,
        String projectId,
        ProjectSubmitRequest request
    ) {
        Project project = locked(projectId);
        owner(user, project);
        String hash = HashUtils.sha256(
            projectId +
                "|" +
                request.version() +
                "|" +
                request.reviewers().stream().sorted().toList()
        );
        Submission receipt = workflow.selectReceipt(user.id(), request.requestId());
        if (receipt != null) {
            require(
                receipt.getProjectId().equals(projectId) && hash.equals(receipt.getRequestHash()),
                409,
                "同一提交标识不能用于不同参数"
            );
            return new SubmissionResponse(projectId, receipt.getRoundNo(), true);
        }
        version(project, request.version());
        require(editable(project), 409, "当前状态不能提交");
        List<ApprovalRoutePlanner.Node> route = planner.plan(project, request.reviewers());
        int round = project.getRoundNo() + 1;
        Submission submission = new Submission();
        submission.setId(UUID.randomUUID().toString());
        submission.setProjectId(projectId);
        submission.setRoundNo(round);
        submission.setSubmitterId(user.id());
        submission.setSubmitterName(user.displayName());
        submission.setOrgId(project.getOrgId());
        submission.setOrgName(users.selectOrganization(project.getOrgId()).getName());
        submission.setProjectCode(project.getProjectCode());
        submission.setProjectName(project.getProjectName());
        submission.setAmount(project.getAmount());
        submission.setMaterial(project.getMaterial());
        submission.setIdempotencyKey(request.requestId());
        submission.setRequestHash(hash);
        changed(workflow.insertSubmission(submission));
        String first = null;
        int seq = 0;
        for (ApprovalRoutePlanner.Node node : route) {
            ApprovalStep step = new ApprovalStep();
            step.setId(UUID.randomUUID().toString());
            step.setProjectId(projectId);
            step.setRoundNo(round);
            step.setSeq(++seq);
            step.setOrgId(node.organization().getId());
            step.setOrgName(node.organization().getName());
            step.setStatus(seq == 1 ? "PENDING" : "WAITING");
            if (seq == 1) {
                first = step.getId();
                step.setStartedAt(LocalDateTime.now(ZoneId.of("Asia/Shanghai")));
            }
            changed(workflow.insertStep(step));
            List<ApprovalAssignee> assignees = new ArrayList<>();
            for (AppUser reviewer : node.reviewers()) {
                ApprovalAssignee a = new ApprovalAssignee();
                a.setStepId(step.getId());
                a.setUserId(reviewer.getId());
                a.setUsername(reviewer.getUsername());
                a.setDisplayName(reviewer.getDisplayName());
                a.setStatus(step.getStatus());
                assignees.add(a);
            }
            require(workflow.insertAssignees(assignees) == assignees.size(), 409, "候选人保存失败");
        }
        changed(projects.progress(projectId, project.getVersion(), "PENDING", round, first));
        record(
            project,
            user,
            round,
            first,
            "SUBMIT",
            project.getStatus(),
            "PENDING",
            project.getVersion(),
            project.getVersion() + 1,
            request.reviewers().isEmpty() ? "跳过本级，向上提交" : "本级或签，通过后逐级上报"
        );
        return new SubmissionResponse(projectId, round, false);
    }

    @Override
    @Transactional
    public void review(CurrentUser user, String projectId, ProjectReviewRequest request) {
        Project project = locked(projectId);
        version(project, request.version());
        require(
            "PENDING".equals(project.getStatus()) &&
                request.stepId().equals(project.getCurrentStepId()),
            409,
            "当前节点已变化或已被处理"
        );
        require(project.getCreatorId() != user.id(), 403, "不能审核自己填报的材料");
        require(workflow.isPending(request.stepId(), user.id()), 403, "你不是当前节点的待办审批人");
        ApprovalStep step = workflow.selectStep(request.stepId());
        require(
            step != null &&
                step.getProjectId().equals(projectId) &&
                step.getRoundNo().equals(project.getRoundNo()),
            409,
            "审批节点与材料或轮次不匹配"
        );
        require(step.getOrgId() == user.orgId(), 403, "所属组织已变化，请由填报人撤回后重新分配");
        Submission submission = workflow.selectSubmission(projectId, project.getRoundNo());
        require(
            submission != null && Boolean.TRUE.equals(submission.getSnapshotAvailable()),
            409,
            "历史轮次没有材料快照，请填报人撤回重提"
        );
        boolean approve = request.approved();
        require(approve || !request.opinion().isBlank(), 400, "驳回意见不能为空");
        step.setActorId(user.id());
        step.setActorName(user.displayName());
        step.setOpinion(request.opinion().strip());
        step.setStatus(approve ? "PASSED" : "REJECTED");
        changed(workflow.resolveStep(step));
        require(
            workflow.resolveAssignees(step.getId(), user.id(), step.getStatus()) > 0,
            409,
            "审批任务已变化"
        );
        ApprovalStep next = approve ? workflow.selectNext(projectId, project.getRoundNo()) : null;
        if (!approve) {
            workflow.cancelAssignees(projectId, project.getRoundNo());
            workflow.cancelSteps(projectId, project.getRoundNo());
        }
        if (next != null) {
            changed(workflow.activateStep(next.getId()));
            require(workflow.activateAssignees(next.getId()) > 0, 409, "下级候选人不存在");
        }
        String status = !approve ? "REJECTED" : next == null ? "APPROVED" : "PENDING";
        if (!"PENDING".equals(status)) changed(
            workflow.finishSubmission(projectId, project.getRoundNo(), status)
        );
        changed(
            projects.progress(
                projectId,
                project.getVersion(),
                status,
                project.getRoundNo(),
                next == null ? null : next.getId()
            )
        );
        record(
            project,
            user,
            project.getRoundNo(),
            step.getId(),
            approve ? "APPROVE" : "REJECT",
            "PENDING",
            status,
            project.getVersion(),
            project.getVersion() + 1,
            request.opinion().strip()
        );
    }

    @Override
    @Transactional
    public void withdraw(CurrentUser user, String projectId, WithdrawRequest request) {
        Project project = locked(projectId);
        owner(user, project);
        version(project, request.version());
        require("PENDING".equals(project.getStatus()), 409, "只有审核中的本人材料可以撤回");
        workflow.cancelAssignees(projectId, project.getRoundNo());
        workflow.cancelSteps(projectId, project.getRoundNo());
        changed(workflow.finishSubmission(projectId, project.getRoundNo(), "CANCELLED"));
        changed(
            projects.progress(projectId, project.getVersion(), "DRAFT", project.getRoundNo(), null)
        );
        record(
            project,
            user,
            project.getRoundNo(),
            project.getCurrentStepId(),
            "WITHDRAW",
            "PENDING",
            "DRAFT",
            project.getVersion(),
            project.getVersion() + 1,
            request.reason().strip()
        );
    }

    @Override
    @Transactional
    public void delete(CurrentUser user, String projectId, long version) {
        Project project = locked(projectId);
        owner(user, project);
        version(project, version);
        require(
            "DRAFT".equals(project.getStatus()) && project.getRoundNo() == 0,
            409,
            "仅从未提交的草稿允许删除，历史材料保留审计"
        );
        changed(projects.softDelete(projectId, version));
        record(
            project,
            user,
            null,
            null,
            "DELETE",
            "DRAFT",
            "DRAFT",
            project.getVersion(),
            project.getVersion() + 1,
            "逻辑删除未提交草稿"
        );
    }

    private void record(
        Project project,
        CurrentUser user,
        Integer round,
        String step,
        String action,
        String before,
        String after,
        Long beforeVersion,
        Long afterVersion,
        String note
    ) {
        ProjectEvent event = new ProjectEvent();
        event.setProjectId(project.getId());
        event.setRoundNo(round);
        event.setStepId(step);
        event.setActorId(user.id());
        event.setActorName(user.displayName());
        event.setAction(action);
        event.setNote(note);
        event.setBeforeStatus(before);
        event.setAfterStatus(after);
        event.setBeforeVersion(beforeVersion);
        event.setAfterVersion(afterVersion);
        changed(workflow.insertEvent(event));
    }
}
