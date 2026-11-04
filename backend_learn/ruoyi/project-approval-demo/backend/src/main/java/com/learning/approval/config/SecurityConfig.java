package com.learning.approval.config;

import com.learning.approval.security.*;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.*;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

@Configuration
@EnableMethodSecurity
@EnableConfigurationProperties(SecurityProperties.class)
public class SecurityConfig {

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder(12);
    }

    @Bean
    SecurityFilterChain securityFilterChain(
        HttpSecurity http,
        JwtAuthenticationFilter filter,
        SecurityErrorWriter errors
    ) throws Exception {
        return http
            .csrf(csrf -> csrf.disable())
            .formLogin(form -> form.disable())
            .httpBasic(basic -> basic.disable())
            .logout(logout -> logout.disable())
            .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .exceptionHandling(e ->
                e
                    .authenticationEntryPoint((request, response, error) ->
                        errors.write(response, 401, "请先登录")
                    )
                    .accessDeniedHandler((request, response, error) ->
                        errors.write(response, 403, "没有此操作权限")
                    )
            )
            .authorizeHttpRequests(r ->
                r
                    .requestMatchers("/api/auth/login", "/actuator/health", "/error")
                    .permitAll()
                    .anyRequest()
                    .authenticated()
            )
            .addFilterBefore(filter, UsernamePasswordAuthenticationFilter.class)
            .build();
    }

    /** 过滤器只加入Security链，避免作为Servlet过滤器再次注册。 */
    @Bean
    FilterRegistrationBean<JwtAuthenticationFilter> jwtRegistration(
        JwtAuthenticationFilter filter
    ) {
        var registration = new FilterRegistrationBean<>(filter);
        registration.setEnabled(false);
        return registration;
    }
}
