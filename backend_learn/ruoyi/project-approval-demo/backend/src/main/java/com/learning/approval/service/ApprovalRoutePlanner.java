package com.learning.approval.service;

import com.learning.approval.domain.*;
import java.util.List;

public interface ApprovalRoutePlanner {
    record Node(Organization organization, List<AppUser> reviewers) {}

    List<Node> plan(Project project, List<Long> selected);
}
