package com.aisense.hello;

import java.util.Scanner;

public class ScannerDemo {
    public static void main(String[] args) {
        Scanner sc=new Scanner(System.in);
        System.out.println("请输入您的年龄");
        int age=sc.nextInt();//执行到这里停住
        System.out.println("请输入您的姓名");
        String name = sc.next();
        System.out.println(name+"欢迎您");
    }
}
