package com.learn.approval;

import org.junit.jupiter.api.*;

import static org.junit.jupiter.api.Assertions.assertEquals;

public class ScoreTest {

    @BeforeAll
    public static void beforeAll() {
        System.out.println("beforeAll");
    }
    @AfterAll
    public static void AfterAll() {
        System.out.println("AfterAll");
    }
    @BeforeEach
    public void BeforeEach() {
        System.out.println("Before Each");
    }
    @AfterEach
    public void AfterEach() {
        System.out.println("After Each");
    }

    @Test
    void shouldCalculateAverage() {
        double[] scores = {80, 90, 100};

        double sum = 0;
        for (double score : scores) {
            sum += score;
        }
        double average = sum / scores.length;

        assertEquals(90.0, average, 0.001);
    }
}
