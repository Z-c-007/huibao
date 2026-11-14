package com.aisense.hello;

public class HelloWorld {
    public static void main(String[] args) {
//        System.out.println("hello world111");
//        int age=2;
//        System.out.println(age);
        //自动类型转换 小范围类型自动转换为大范围类型，以及byte short在参与运算的时候自动转换为int类型
//        byte a =1;
//        int b= a;
//        System.out.println(a);
//        System.out.println(b);
        // 强制类型转换  byte b=(byte) a 强制类型转换会出问题，double也就是小数做强制类型转换的时候是去掉小数点
        int a=200;
        byte b=(byte) a;
        System.out.println(a);
        System.out.println(b);
    }
}
