package demo.great.dao;

import demo.great.entity.User;
import demo.great.entity.BillItem;
import java.util.List;

public interface UserDao {
    int createUser(User user);
    int updateUser(User user);
    int deleteUser(Integer id);
    User loadUser(Integer id);
    User loadUser(Integer id, boolean master);
    List<User> listUsers(String username, String nickname);
    List<User> listUsers(String username, String nickname, boolean master);
    List<BillItem> listUserExpenses(Integer userId);
    List<BillItem> listUserIncomes(Integer userId);
    BillItem getLastUserExpense(Integer userId);
    BillItem getLastUserIncome(Integer userId);
}
