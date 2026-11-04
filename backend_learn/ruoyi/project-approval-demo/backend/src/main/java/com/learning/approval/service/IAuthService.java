package com.learning.approval.service;

import com.learning.approval.dto.request.*;
import com.learning.approval.dto.response.*;
import com.learning.approval.security.CurrentUser;
import java.util.List;

public interface IAuthService {
    LoginResponse login(LoginRequest request, String ip, String userAgent);
    void logout(String sessionId);
    List<SessionResponse> sessions(CurrentUser user, String currentSessionId);
    void revokeSession(CurrentUser user, String sessionId);
    void changePassword(CurrentUser user, PasswordRequest request);
}
