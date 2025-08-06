package demo.great.dao.mapper;

import demo.great.entity.User;
import org.apache.ibatis.annotations.Mapper;
import java.util.List;

/**
 * 用户Mapper接口
 * 
 * @author demo
 */
@Mapper
public interface UserMapper {
    
    /**
     * 根据ID查询用户
     */
    User selectById(Long id);
    
    /**
     * 查询所有用户
     */
    List<User> selectAll();
    
    /**
     * 插入用户
     */
    int insert(User user);
    
    /**
     * 更新用户
     */
    int update(User user);
    
    /**
     * 删除用户
     */
    int deleteById(Long id);
    
    /**
     * 根据用户名查询用户
     */
    User selectByUsername(String username);
}