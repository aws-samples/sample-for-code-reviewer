package demo.great.service;

import demo.great.base.GreatException;
import demo.great.dao.UserDao;
import demo.great.dao.BillItemDao;
import demo.great.entity.User;
import demo.great.entity.BillItem;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.TransactionStatus;
import org.springframework.transaction.support.DefaultTransactionDefinition;

import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class UserService {
    private static final Logger logger = LoggerFactory.getLogger(UserService.class);

    @Autowired
    private UserDao userDao;

    @Autowired
    private BillItemDao billItemDao;

    @Autowired
    private PlatformTransactionManager transactionManager;

    public int createUser(String username, String nickname, String password) {
        try {
            User user = new User();
            user.setUsername(username);
            user.setNickname(nickname);
            user.setPassword(password);
            return userDao.createUser(user);
        } catch (Exception e) {
            logger.error("Failed to create user", e);
            throw new GreatException("Failed to create user", e);
        }
    }

    public int updateUser(Integer id, String username, String nickname, String password) {
        try {
            User user = userDao.loadUser(id, true);
            if (user == null) {
                throw new GreatException("User not found with id: " + id);
            }
            user.setUsername(username);
            user.setNickname(nickname);
            user.setPassword(password);
            return userDao.updateUser(user);
        } catch (Exception e) {
            logger.error("Failed to update user", e);
            throw new GreatException("Failed to update user", e);
        }
    }

    public int deleteUser(Integer id) {
        try {
            int rowsDeleted = userDao.deleteUser(id);
            return rowsDeleted > 0 ? id : 0;
        } catch (Exception e) {
            logger.error("Failed to delete user", e);
            throw new GreatException("Failed to delete user", e);
        }
    }

    public User loadUser(Integer id) {
        try {
            return userDao.loadUser(id);
        } catch (Exception e) {
            logger.error("Failed to load user", e);
            throw new GreatException("Failed to load user", e);
        }
    }

    public List<User> listUsers(String username, String nickname) {
        try {
            return userDao.listUsers(username, nickname);
        } catch (Exception e) {
            logger.error("Failed to list users", e);
            throw new GreatException("Failed to list users", e);
        }
    }

    @Transactional
    public Map<String, Object> recordBill(Integer userId, Integer categoryId, String billType, Date billDate, Integer amount, String description) {
        Map<String, Object> result = new HashMap<>();
        DefaultTransactionDefinition def = new DefaultTransactionDefinition();
        def.setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRED);
        TransactionStatus status = transactionManager.getTransaction(def);

        try {
            // 1. 记录新的账单明细
            BillItem newItem = new BillItem();
            newItem.setUserId(userId);
            newItem.setCategoryId(categoryId);
            newItem.setBillDate(billDate);
            newItem.setBillType(billType);
            newItem.setAmount(amount);
            newItem.setDescription(description);
            billItemDao.createItem(newItem);

            // 2. 更新great_user表中的last_bill_time字段
            User user = userDao.loadUser(userId, true);
            user.setLastBillTime(billDate);
            userDao.updateUser(user);

            // 3. 获取用户的支出和收入总金额
            List<BillItem> expenses = userDao.listUserExpenses(userId);
            List<BillItem> incomes = userDao.listUserIncomes(userId);
            int totalExpense = expenses.stream().mapToInt(BillItem::getAmount).sum();
            int totalIncome = incomes.stream().mapToInt(BillItem::getAmount).sum();

            // 4. 获取用户最近的支出和收入记录
            BillItem lastExpense = userDao.getLastUserExpense(userId);
            BillItem lastIncome = userDao.getLastUserIncome(userId);

            // 5. 构建结果Map并返回
            result.put("userId", userId);
            result.put("username", user.getUsername());
            result.put("totalExpense", totalExpense);
            result.put("totalIncome", totalIncome);
            result.put("lastExpense", lastExpense);
            result.put("lastIncome", lastIncome);

            transactionManager.commit(status);
        } catch (Exception e) {
            transactionManager.rollback(status);
            throw new GreatException("Failed to record bill", e);
        }

        return result;
    }

    
}
