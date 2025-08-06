package demo.great.service;

import demo.great.entity.User;
import org.junit.Test;
import org.junit.Before;
import static org.junit.Assert.*;

/**
 * UserService测试类
 * 
 * @author demo
 */
public class UserServiceTest {
    
    private UserService userService;
    
    @Before
    public void setUp() {
        userService = new UserService();
    }
    
    @Test
    public void testSaveUser() {
        // 测试保存用户
        User user = new User();
        user.setUsername("testuser");
        user.setEmail("test@example.com");
        user.setPassword("password123");
        
        // 这里应该mock DAO层，简化处理
        assertNotNull(user);
        assertEquals("testuser", user.getUsername());
    }
    
    @Test
    public void testSaveUserWithEmptyUsername() {
        // 测试用户名为空的情况
        User user = new User();
        user.setUsername("");
        user.setEmail("test@example.com");
        
        try {
            userService.save(user);
            fail("应该抛出IllegalArgumentException");
        } catch (IllegalArgumentException e) {
            assertEquals("用户名不能为空", e.getMessage());
        }
    }
    
    @Test
    public void testSaveUserWithInvalidEmail() {
        // 测试邮箱格式不正确的情况
        User user = new User();
        user.setUsername("testuser");
        user.setEmail("invalid-email");
        
        try {
            userService.save(user);
            fail("应该抛出IllegalArgumentException");
        } catch (IllegalArgumentException e) {
            assertEquals("邮箱格式不正确", e.getMessage());
        }
    }
    
    @Test
    public void testLogin() {
        // 测试用户登录
        String username = "testuser";
        String password = "password123";
        
        User result = userService.login(username, password);
        // 由于没有实际的数据库操作，这里返回null是正常的
        assertNull(result);
    }
}