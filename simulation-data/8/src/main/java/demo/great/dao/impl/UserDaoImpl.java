package demo.great.dao.impl;

import demo.great.base.GreatException;
import demo.great.config.DataSourceContextHolder;
import demo.great.dao.UserDao;
import demo.great.dao.mapper.UserMapper;
import demo.great.entity.User;
import demo.great.entity.BillItem;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Repository
@Transactional
public class UserDaoImpl implements UserDao {
    private static final Logger logger = LoggerFactory.getLogger(UserDaoImpl.class);

    @Autowired
    private UserMapper userMapper;

    @Override
    public int createUser(User user) {
        DataSourceContextHolder.write();
        try {
            userMapper.createUser(user);
            return user.getId();
        } catch (Exception e) {
            logger.error("Failed to create user", e);
            throw new GreatException("Failed to create user", e);
        } finally {
            DataSourceContextHolder.clearDataSourceType();
        }
    }

    @Override
    public int updateUser(User user) {
        DataSourceContextHolder.write();
        try {
            int rowsUpdated = userMapper.updateUser(user);
            if (rowsUpdated > 0) {
                return user.getId();
            } else {
                throw new GreatException("User not found with id: " + user.getId());
            }
        } catch (Exception e) {
            logger.error("Failed to update user", e);
            throw new GreatException("Failed to update user", e);
        } finally {
            DataSourceContextHolder.clearDataSourceType();
        }
    }

    @Override
    public int deleteUser(Integer id) {
        DataSourceContextHolder.write();
        try {
            int rowsDeleted = userMapper.deleteUser(id);
            return rowsDeleted;
        } catch (Exception e) {
            logger.error("Failed to delete user", e);
            throw new GreatException("Failed to delete user", e);
        } finally {
            DataSourceContextHolder.clearDataSourceType();
        }
    }

    @Override
    public User loadUser(Integer id) {
        DataSourceContextHolder.read();
        try {
            return userMapper.loadUser(id);
        } catch (Exception e) {
            logger.error("Failed to load user", e);
            throw new GreatException("Failed to load user", e);
        } finally {
            DataSourceContextHolder.clearDataSourceType();
        }
    }

    @Override
    public User loadUser(Integer id, boolean master) {
        if (master) {
            DataSourceContextHolder.write();
        } else {
            DataSourceContextHolder.read();
        }
        try {
            return userMapper.loadUser(id);
        } catch (Exception e) {
            logger.error("Failed to load user", e);
            throw new GreatException("Failed to load user", e);
        } finally {
            DataSourceContextHolder.clearDataSourceType();
        }
    }

    @Override
    public List<User> listUsers(String username, String nickname) {
        DataSourceContextHolder.read();
        try {
            return userMapper.listUsers(username, nickname);
        } catch (Exception e) {
            logger.error("Failed to list users", e);
            throw new GreatException("Failed to list users", e);
        } finally {
            DataSourceContextHolder.clearDataSourceType();
        }
    }

    @Override
    public List<User> listUsers(String username, String nickname, boolean master) {
        if (master) {
            DataSourceContextHolder.write();
        } else {
            DataSourceContextHolder.read();
        }
        try {
            return userMapper.listUsers(username, nickname);
        } catch (Exception e) {
            logger.error("Failed to list users", e);
            throw new GreatException("Failed to list users", e);
        } finally {
            DataSourceContextHolder.clearDataSourceType();
        }
    }

    @Override
    public List<BillItem> listUserExpenses(Integer userId) {
        DataSourceContextHolder.read();
        try {
            return userMapper.listUserExpenses(userId);
        } catch (Exception e) {
            logger.error("Failed to list user expenses", e);
            throw new GreatException("Failed to list user expenses", e);
        } finally {
            DataSourceContextHolder.clearDataSourceType();
        }
    }

    @Override
    public List<BillItem> listUserIncomes(Integer userId) {
        DataSourceContextHolder.read();
        try {
            return userMapper.listUserIncomes(userId);
        } catch (Exception e) {
            logger.error("Failed to list user incomes", e);
            throw new GreatException("Failed to list user incomes", e);
        } finally {
            DataSourceContextHolder.clearDataSourceType();
        }
    }

    @Override
    public BillItem getLastUserExpense(Integer userId) {
        DataSourceContextHolder.read();
        try {
            return userMapper.getLastUserExpense(userId);
        } catch (Exception e) {
            logger.error("Failed to get last user expense", e);
            throw new GreatException("Failed to get last user expense", e);
        } finally {
            DataSourceContextHolder.clearDataSourceType();
        }
    }

    @Override
    public BillItem getLastUserIncome(Integer userId) {
        DataSourceContextHolder.read();
        try {
            return userMapper.getLastUserIncome(userId);
        } catch (Exception e) {
            logger.error("Failed to get last user income", e);
            throw new GreatException("Failed to get last user income", e);
        } finally {
            DataSourceContextHolder.clearDataSourceType();
        }
    }
}
