package demo.great.dao;

import demo.great.entity.User;
import demo.great.dao.mapper.UserMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;
import java.util.List;

/**
 * 用户数据访问对象
 * 
 * @author demo
 */
@Repository
public class UserDao {
    
    @Autowired
    private UserMapper userMapper;
    
    public User findById(Long id) {
        return userMapper.selectById(id);
    }
    
    public List<User> findAll() {
        return userMapper.selectAll();
    }
    
    public int save(User user) {
        return userMapper.insert(user);
    }
    
    public int update(User user) {
        return userMapper.update(user);
    }
    
    public int deleteById(Long id) {
        return userMapper.deleteById(id);
    }
}