package com.learning.approval.security;

import java.util.List;

public record SessionRevocationEvent(List<Long> userIds) {}
