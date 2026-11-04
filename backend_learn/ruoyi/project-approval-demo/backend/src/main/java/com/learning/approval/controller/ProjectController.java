package com.learning.approval.controller;

import com.learning.approval.audit.AuditAction;
import com.learning.approval.common.*;
import com.learning.approval.domain.ProjectView;
import com.learning.approval.dto.request.*;
import com.learning.approval.dto.response.*;
import com.learning.approval.security.CurrentUser;
import com.learning.approval.service.IProjectService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.util.List;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

@Validated
@RestController
@RequestMapping("/api")
public class ProjectController {

    private final IProjectService service;

    public ProjectController(IProjectService service) {
        this.service = service;
    }

    @GetMapping("/projects")
    @PreAuthorize("hasAuthority('approval:report:list')")
    public ApiResponse<PageResult<ProjectView>> mine(
        @AuthenticationPrincipal CurrentUser user,
        @RequestParam(defaultValue = "1") @Min(1) @Max(100000) int page,
        @RequestParam(defaultValue = "10") @Min(1) @Max(50) int size,
        @RequestParam(defaultValue = "") @Pattern(
            regexp = "DRAFT|PENDING|APPROVED|REJECTED|"
        ) String status
    ) {
        return ApiResponse.success(service.mine(user, page, size, status));
    }

    @GetMapping("/review-tasks")
    @PreAuthorize("hasAuthority('approval:review:list')")
    public ApiResponse<PageResult<ProjectView>> tasks(
        @AuthenticationPrincipal CurrentUser user,
        @RequestParam(defaultValue = "1") @Min(1) @Max(100000) int page,
        @RequestParam(defaultValue = "10") @Min(1) @Max(50) int size,
        @RequestParam(defaultValue = "") @Pattern(
            regexp = "PENDING|APPROVED|REJECTED|CANCELLED|"
        ) String status,
        @RequestParam(defaultValue = "PENDING") @Pattern(
            regexp = "PENDING|PROCESSED"
        ) String taskState
    ) {
        return ApiResponse.success(service.tasks(user, page, size, status, taskState));
    }

    @GetMapping("/projects/reviewers")
    @PreAuthorize("hasAnyAuthority('approval:report:add','approval:report:submit')")
    public ApiResponse<List<ReviewerResponse>> reviewers(
        @AuthenticationPrincipal CurrentUser user,
        @RequestParam(required = false) String projectId
    ) {
        return ApiResponse.success(service.reviewers(user, projectId));
    }

    @GetMapping("/projects/{id}")
    @PreAuthorize("hasAnyAuthority('approval:report:query','approval:review:query')")
    public ApiResponse<ProjectDetailResponse> detail(
        @AuthenticationPrincipal CurrentUser user,
        @PathVariable String id,
        @RequestParam(required = false) @Positive Integer roundNo
    ) {
        return ApiResponse.success(service.detail(user, id, roundNo));
    }

    @PostMapping("/projects")
    @PreAuthorize("hasAuthority('approval:report:add')")
    @AuditAction("CREATE_PROJECT")
    public ApiResponse<ProjectView> create(
        @AuthenticationPrincipal CurrentUser user,
        @Valid @RequestBody ProjectSaveRequest body
    ) {
        return ApiResponse.success(service.create(user, body));
    }

    @PutMapping("/projects/{id}")
    @PreAuthorize("hasAuthority('approval:report:edit')")
    @AuditAction("UPDATE_PROJECT")
    public ApiResponse<ProjectView> update(
        @AuthenticationPrincipal CurrentUser user,
        @PathVariable String id,
        @Valid @RequestBody ProjectSaveRequest body
    ) {
        return ApiResponse.success(service.update(user, id, body));
    }

    @PostMapping("/projects/{id}/submit")
    @PreAuthorize("hasAuthority('approval:report:submit')")
    @AuditAction("SUBMIT_PROJECT")
    public ApiResponse<SubmissionResponse> submit(
        @AuthenticationPrincipal CurrentUser user,
        @PathVariable String id,
        @Valid @RequestBody ProjectSubmitRequest body
    ) {
        return ApiResponse.success(service.submit(user, id, body));
    }

    @PostMapping("/projects/{id}/review")
    @PreAuthorize("hasAuthority('approval:review:audit')")
    @AuditAction("REVIEW_PROJECT")
    public ApiResponse<Boolean> review(
        @AuthenticationPrincipal CurrentUser user,
        @PathVariable String id,
        @Valid @RequestBody ProjectReviewRequest body
    ) {
        service.review(user, id, body);
        return ApiResponse.success(true);
    }

    @PostMapping("/projects/{id}/withdraw")
    @PreAuthorize("hasAuthority('approval:report:withdraw')")
    @AuditAction("WITHDRAW_PROJECT")
    public ApiResponse<Boolean> withdraw(
        @AuthenticationPrincipal CurrentUser user,
        @PathVariable String id,
        @Valid @RequestBody WithdrawRequest body
    ) {
        service.withdraw(user, id, body);
        return ApiResponse.success(true);
    }

    @DeleteMapping("/projects/{id}")
    @PreAuthorize("hasAuthority('approval:report:delete')")
    @AuditAction("DELETE_DRAFT")
    public ApiResponse<Boolean> delete(
        @AuthenticationPrincipal CurrentUser user,
        @PathVariable String id,
        @RequestParam @Min(0) long version
    ) {
        service.delete(user, id, version);
        return ApiResponse.success(true);
    }
}
