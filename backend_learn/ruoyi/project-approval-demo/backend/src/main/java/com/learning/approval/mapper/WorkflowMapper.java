package com.learning.approval.mapper;

import com.learning.approval.domain.*;
import java.util.List;
import org.apache.ibatis.annotations.Param;

public interface WorkflowMapper {
    int insertSubmission(Submission submission);
    Submission selectSubmission(
        @Param("projectId") String projectId,
        @Param("roundNo") int roundNo
    );
    Submission selectReceipt(@Param("userId") long userId, @Param("key") String key);
    List<Submission> selectSubmissions(String projectId);
    int finishSubmission(
        @Param("projectId") String projectId,
        @Param("roundNo") int roundNo,
        @Param("status") String status
    );
    int insertStep(ApprovalStep step);
    int insertAssignees(@Param("assignees") List<ApprovalAssignee> assignees);
    List<ApprovalStep> selectSteps(
        @Param("projectId") String projectId,
        @Param("roundNo") Integer roundNo
    );
    List<ApprovalAssignee> selectAssignees(
        @Param("projectId") String projectId,
        @Param("roundNo") Integer roundNo
    );
    ApprovalStep selectStep(String stepId);
    ApprovalStep selectNext(@Param("projectId") String projectId, @Param("roundNo") int roundNo);
    boolean hasReached(
        @Param("projectId") String projectId,
        @Param("roundNo") int roundNo,
        @Param("userId") long userId
    );
    boolean isPending(@Param("stepId") String stepId, @Param("userId") long userId);
    int resolveStep(ApprovalStep step);
    int resolveAssignees(
        @Param("stepId") String stepId,
        @Param("userId") long userId,
        @Param("status") String status
    );
    int activateStep(String stepId);
    int activateAssignees(String stepId);
    int cancelAssignees(@Param("projectId") String projectId, @Param("roundNo") int roundNo);
    int cancelSteps(@Param("projectId") String projectId, @Param("roundNo") int roundNo);
    int insertEvent(ProjectEvent event);
    List<ProjectEvent> selectEvents(
        @Param("projectId") String projectId,
        @Param("roundNo") Integer roundNo
    );
}
