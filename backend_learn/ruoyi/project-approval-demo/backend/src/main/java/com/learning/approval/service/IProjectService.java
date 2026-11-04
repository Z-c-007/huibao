package com.learning.approval.service;

import com.learning.approval.common.PageResult;
import com.learning.approval.domain.ProjectView;
import com.learning.approval.dto.request.*;
import com.learning.approval.dto.response.*;
import com.learning.approval.security.CurrentUser;
import java.util.List;

public interface IProjectService {
    PageResult<ProjectView> mine(CurrentUser user, int page, int size, String status);
    PageResult<ProjectView> tasks(
        CurrentUser user,
        int page,
        int size,
        String status,
        String taskState
    );
    List<ReviewerResponse> reviewers(CurrentUser user, String projectId);
    ProjectDetailResponse detail(CurrentUser user, String projectId, Integer roundNo);
    ProjectView create(CurrentUser user, ProjectSaveRequest request);
    ProjectView update(CurrentUser user, String projectId, ProjectSaveRequest request);
    SubmissionResponse submit(CurrentUser user, String projectId, ProjectSubmitRequest request);
    void review(CurrentUser user, String projectId, ProjectReviewRequest request);
    void withdraw(CurrentUser user, String projectId, WithdrawRequest request);
    void delete(CurrentUser user, String projectId, long version);
}
