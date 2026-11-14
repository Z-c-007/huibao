package com.learning.tests;

import java.util.Scanner;

public class Test {
    public static void main(String[] args) {
        double[] scores = new double[8];
        Scanner sc = new Scanner(System.in);
        for (int i = 0; i < scores.length; i++) {
            System.out.print("请输入第" + (i + 1) + "位学生的成绩：");
            scores[i] = sc.nextDouble();
        }

        // 遍历输出，复习数组的取值方式 scores[i] 和长度 scores.length
        double sum = 0;
        System.out.println("----- 成绩单 -----");
        for (int i = 0; i < scores.length; i++) {
            System.out.println("第" + (i + 1) + "位学生：" + scores[i]);
            sum += scores[i];
        }
        System.out.printf("总分：%.2f，平均分：%.2f%n", sum, sum / scores.length);
    }
}
