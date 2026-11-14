package com.learn.approval;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.MethodSource;
import org.junit.jupiter.params.provider.ValueSource;

import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 参数化测试 + 断言 的完整示例。
 * <p>
 * 共 5 个测试方法，实际产生 16 个用例：
 * passWhenScoreAtLeast60(4) + failWhenScoreBelow60(3) + gradeOf(4)
 * + average(4) + averageOfEmptyArrayShouldThrow(1)
 */
@DisplayName("分数逻辑：参数化测试与断言")
public class AverageTest   {

    /** 用来观察生命周期：每个用例都会拿到一个全新实例，所以它永远是 1 */
    private int seq;

    @BeforeEach
    void beforeEach() {
        seq++;
        System.out.println("  @BeforeEach 第 " + seq + " 次, 实例 hashCode=" + System.identityHashCode(this));
    }

    @AfterEach
    void afterEach() {
        System.out.println("  @AfterEach 结束,     实例 hashCode=" + System.identityHashCode(this));
    }

    // ==================== ① @ValueSource：1 个参数，多个值，同一个结论 ====================

    @ParameterizedTest(name = "[{index}] {0} 分应该及格")
    @ValueSource(ints = {60, 61, 75, 100})
    void passWhenScoreAtLeast60(int score) {
        assertTrue(Grades.isPass(score), score + " 分应该及格");
    }

    @ParameterizedTest(name = "[{index}] {0} 分应该不及格")
    @ValueSource(ints = {0, 1, 59})
    void failWhenScoreBelow60(int score) {
        assertFalse(Grades.isPass(score), score + " 分应该不及格");
    }

    // ==================== ② @CsvSource：多个参数，一行一条用例 ====================

    @DisplayName("等级判定")
    @ParameterizedTest(name = "[{index}] {0} 分 -> {1}")
    @CsvSource({
            "95, 优秀",
            "85, 良好",
            "60, 及格",
            "59, 不及格"
    })
    void gradeOf(int score, String expectedGrade) {
        assertEquals(expectedGrade, Grades.gradeOf(score), score + " 分的等级不对");
    }

    // ==================== ③ @MethodSource：参数是数组/对象，最灵活 ====================

    @DisplayName("平均分")
    @ParameterizedTest(name = "[{index}] 期望 {1} 分")
    @MethodSource("averageCases")
    void average(double[] scores, double expected) {
        assertEquals(expected, Grades.average(scores), 0.0001);
    }

    /** 工厂方法必须是 static（默认 per-method 生命周期下，此时还没有测试实例） */
    static Stream<Arguments> averageCases() {
        return Stream.of(
                Arguments.of(new double[]{80, 90, 100}, 90.0),
                Arguments.of(new double[]{100}, 100.0),
                Arguments.of(new double[]{0, 0, 0}, 0.0),
                Arguments.of(new double[]{59.5, 60.5}, 60.0)
        );
    }

    // ==================== ④ 普通 @Test 可以和参数化测试混在同一个类里 ====================

    @Test
    void averageOfEmptyArrayShouldThrow() {
        IllegalArgumentException ex = assertThrows(
                IllegalArgumentException.class,
                () -> Grades.average(new double[]{}));
        assertEquals("scores 不能为空", ex.getMessage());
    }
}

/**
 * 演示用的“被测对象”（SUT）。
 * 真实项目里它应该在 src/main/java 下，这里为了让你一个文件就能跑通，才放在同一个文件中。
 */
class Grades {

    /** 规则：60 分及以上及格 */
    static boolean isPass(int score) {
        return score >= 60;
    }

    /** 规则：>=90 优秀，>=80 良好，>=60 及格，其余不及格 */
    static String gradeOf(int score) {
        if (score >= 90) {
            return "优秀";
        }
        if (score >= 80) {
            return "良好";
        }
        if (score >= 60) {
            return "及格";
        }
        return "不及格";
    }

    /** 规则：空数组是非法输入，必须抛异常 */
    static double average(double[] scores) {
        if (scores == null || scores.length == 0) {
            throw new IllegalArgumentException("scores 不能为空");
        }
        double sum = 0;
        for (double score : scores) {
            sum += score;
        }
        return sum / scores.length;
    }
}
