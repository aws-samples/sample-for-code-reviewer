package demo.great;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * 主应用程序入口
 * 
 * @author demo
 * @version 1.0
 */
@SpringBootApplication
public class App {
    
    public static void main(String[] args) {
        SpringApplication.run(App.class, args);
        System.out.println("Demo Java Project started successfully!");
    }
}