package demo.great.dao.mapper;

import demo.great.entity.BillItem;
import demo.great.entity.User;
import org.apache.ibatis.annotations.Mapper;
import java.util.List;

@Mapper
public interface UserMapper {
    int createUser(User user);
    int updateUser(User user);
    int deleteUser(Integer id);
    User loadUser(Integer id);
    List<User> listUsers(String username, String nickname);
    List<BillItem> listUserExpenses(Integer userId);
    List<BillItem> listUserIncomes(Integer userId);
    BillItem getLastUserExpense(Integer userId);
    BillItem getLastUserIncome(Integer userId);
}
