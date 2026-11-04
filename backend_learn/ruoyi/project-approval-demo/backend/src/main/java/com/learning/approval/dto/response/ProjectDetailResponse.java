package com.learning.approval.dto.response;

import com.learning.approval.domain.*;
import java.util.List;

public record ProjectDetailResponse(
    ProjectView project,
    List<Submission> submissions,
    List<ApprovalStep> steps,
    List<ApprovalAssignee> assignees,
    List<ProjectEvent> events,
    boolean canEdit,
    boolean canDelete,
    boolean canSubmit,
    boolean canReview,
    boolean canWithdraw,
    String notice
) {}
