package com.learning.approval.common;

import java.util.List;

public record PageResult<T>(List<T> rows, long total, int pageNum, int pageSize) {}
