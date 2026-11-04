package com.learning.approval.dto.response;

import com.learning.approval.domain.Role;
import java.util.List;

public record RoleResponse(Role role, List<String> permissions) {}
