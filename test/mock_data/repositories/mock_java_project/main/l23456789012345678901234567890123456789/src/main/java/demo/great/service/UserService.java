package demo.great.service;

import demo.great.entity.User;
import demo.great.dao.UserDao;
import demo.great.base.BaseService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import java.util.List;

/**
 * 用户服务类
 * 
 * @author demo
 */
@Service
public class UserService extends BaseService<User> {
    
    @Autowired
    private UserDao userDao;
    
    @Override
    public User findById(Long id) {
        return userDao.findById(id);
    }
    
    @Override
    public List<User> findAll() {
        return userDao.findAll();
    }
    
    @Override
    public User save(User user) {
        // 业务逻辑验证
        if (user.getUsername() == null || user.getUsername().trim().isEmpty()) {
            throw new IllegalArgumentException("用户名不能为空");
        }
        
        if (user.getEmail() == null || !isValidEmail(user.getEmail())) {
            throw new IllegalArgumentException("邮箱格式不正确");
        }
        
        // 检查用户名是否已存在
        User existingUser = findByUsername(user.getUsername());
        if (existingUser != null) {
            throw new IllegalArgumentException("用户名已存在");
        }
        
        return userDao.save(user);
    }
    
    @Override
    public void deleteById(Long id) {
        userDao.deleteById(id);
    }
    
    @Override
    public User update(User user) {
        return userDao.update(user);
    }
    
    /**
     * 根据用户名查询用户
     */
    public User findByUsername(String username) {
        // 这里应该调用DAO方法，简化处理
        return null;
    }
    
    /**
     * 验证邮箱格式
     */
    private boolean isValidEmail(String email) {
        return email != null && email.contains("@") && email.contains(".");
    }
    
    /**
     * 用户登录验证
     */
    public User login(String username, String password) {
        User user = findByUsername(username);
        if (user != null && user.getPassword().equals(password)) {
            return user;
        }
        return null;
    }
}