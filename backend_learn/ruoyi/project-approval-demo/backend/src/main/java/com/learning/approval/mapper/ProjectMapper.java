package com.learning.approval.mapper;

import com.learning.approval.domain.*;
import java.util.List;
import org.apache.ibatis.annotations.Param;

public interface ProjectMapper {
    long countMine(@Param("userId") long userId, @Param("status") String status);
    List<ProjectView> selectMine(
        @Param("userId") long userId,
        @Param("status") String status,
        @Param("limit") int limit,
        @Param("offset") int offset
    );
    long countTasks(
        @Param("userId") long userId,
        @Param("taskState") String taskState,
        @Param("status") String status
    );
    List<ProjectView> selectTasks(
        @Param("userId") long userId,
        @Param("taskState") String taskState,
        @Param("status") String status,
        @Param("limit") int limit,
        @Param("offset") int offset
    );
    Project selectForUpdate(String projectId);
    ProjectView selectDetail(String projectId);
    int insert(Project project);
    int updateContent(Project project);
    int softDelete(@Param("id") String id, @Param("version") long version);
    int progress(
        @Param("id") String id,
        @Param("version") long version,
        @Param("status") String status,
        @Param("roundNo") int roundNo,
        @Param("stepId") String stepId
    );
}
