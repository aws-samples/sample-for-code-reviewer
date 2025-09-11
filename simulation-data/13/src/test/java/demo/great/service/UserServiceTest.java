package demo.great.service;

import demo.great.entity.User;
import demo.great.entity.BillCategory;
import demo.great.entity.BillItem;
import demo.great.service.BillCategoryService;
import demo.great.dao.BillItemDao;
import demo.great.dao.UserDao;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.UUID;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
public class UserServiceTest {

    @Autowired
    private UserService userService;

    @Autowired
    private BillCategoryService billCategoryService;

    @Autowired
    private BillItemDao billItemDao;

    @Autowired
    private UserDao userDao;

    private static final Random RANDOM = new Random();

    private String generateRandomString(int length) {
        StringBuilder sb = new StringBuilder(length);
        for (int i = 0; i < length; i++) {
            sb.append((char) ('a' + RANDOM.nextInt(26)));
        }
        return sb.toString();
    }

    private String generateUniquePrefix() {
        return UUID.randomUUID().toString().substring(0, 8);
    }

    @Test
    public void testCreateUser() {
        String prefix = generateUniquePrefix();
        String username = prefix + generateRandomString(6);
        String nickname = prefix + generateRandomString(6);
        String password = generateRandomString(10);

        int userId = userService.createUser(username, nickname, password);
        assertTrue(userId > 0);

        User user = userService.loadUser(userId);
        assertNotNull(user);
        assertEquals(username, user.getUsername());
        assertEquals(nickname, user.getNickname());
        assertEquals(password, user.getPassword());
    }

    @Test
    public void testUpdateUser() {
        String prefix = generateUniquePrefix();
        String username = prefix + generateRandomString(6);
        String nickname = prefix + generateRandomString(6);
        String password = generateRandomString(10);

        int userId = userService.createUser(username, nickname, password);
        assertTrue(userId > 0);

        String newUsername = prefix + generateRandomString(6);
        String newNickname = prefix + generateRandomString(6);
        String newPassword = generateRandomString(10);

        int updatedUserId = userService.updateUser(userId, newUsername, newNickname, newPassword);
        assertEquals(userId, updatedUserId);

        User user = userService.loadUser(userId);
        assertNotNull(user);
        assertEquals(newUsername, user.getUsername());
        assertEquals(newNickname, user.getNickname());
        assertEquals(newPassword, user.getPassword());
    }

    @Test
    public void testDeleteUser() {
        String prefix = generateUniquePrefix();
        String username = prefix + generateRandomString(6);
        String nickname = prefix + generateRandomString(6);
        String password = generateRandomString(10);

        int userId = userService.createUser(username, nickname, password);
        assertTrue(userId > 0);

        int deletedUserId = userService.deleteUser(userId);
        assertEquals(userId, deletedUserId);

        User user = userService.loadUser(userId);
        assertNull(user);
    }

    @Test
    public void testLoadUser() {
        String prefix = generateUniquePrefix();
        String username = prefix + generateRandomString(6);
        String nickname = prefix + generateRandomString(6);
        String password = generateRandomString(10);

        int userId = userService.createUser(username, nickname, password);
        assertTrue(userId > 0);

        User user = userService.loadUser(userId);
        assertNotNull(user);
        assertEquals(username, user.getUsername());
        assertEquals(nickname, user.getNickname());
        assertEquals(password, user.getPassword());
    }

    @Test
    public void testListUsers() {
        String prefix = generateUniquePrefix();
        String username1 = prefix + generateRandomString(6);
        String nickname1 = prefix + generateRandomString(6);
        String password1 = generateRandomString(10);

        String username2 = prefix + generateRandomString(6);
        String nickname2 = prefix + generateRandomString(6);
        String password2 = generateRandomString(10);

        int userId1 = userService.createUser(username1, nickname1, password1);
        int userId2 = userService.createUser(username2, nickname2, password2);

        List<User> users = userService.listUsers(prefix + "%", prefix + "%");
        assertNotNull(users);
        assertEquals(2, users.size());

        users = userService.listUsers(username1, null);
        assertNotNull(users);
        assertEquals(1, users.size());
        assertEquals(username1, users.get(0).getUsername());

        users = userService.listUsers(null, nickname2);
        assertNotNull(users);
        assertEquals(1, users.size());
        assertEquals(nickname2, users.get(0).getNickname());
    }

    
    @Test
    public void testRecordBill() {
        String prefix = generateUniquePrefix();
        String username = prefix + generateRandomString(6);
        String nickname = prefix + generateRandomString(6);
        String password = generateRandomString(10);

        int userId = userService.createUser(username, nickname, password);
        assertTrue(userId > 0);

        String categoryName = "Category A " + generateRandomString(10);
        String categoryDescription = "This is Category A with random description";
        int categoryId = billCategoryService.createCategory(categoryName, categoryDescription);
        BillCategory categoryA = billCategoryService.loadCategory(categoryId);

        List<BillItem> expenses = userDao.listUserExpenses(userId);
        List<BillItem> incomes = userDao.listUserIncomes(userId);
        int initialTotalExpense = expenses.stream().mapToInt(BillItem::getAmount).sum();
        int initialTotalIncome = incomes.stream().mapToInt(BillItem::getAmount).sum();

        int numRecords = RANDOM.nextInt(6) + 5; // 5 to 10 records
        int totalExpenseIncrease = 0;
        int totalIncomeIncrease = 0;
        boolean hasRecordedExpense = false;
        boolean hasRecordedIncome = false;
        for (int i = 0; i < numRecords; i++) {
            String billType = RANDOM.nextBoolean() ? "expense" : "income";
            Date billDate = new Date();
            int amount = RANDOM.nextInt(10000) + 1; // 1 to 10000
            String description = generateRandomString(20);

            Map<String, Object> result = userService.recordBill(userId, categoryA.getId(), billType, billDate, amount, description);

            int totalExpense = (int) result.get("totalExpense");
            int totalIncome = (int) result.get("totalIncome");

            assertEquals(userId, result.get("userId"));
            assertEquals(username, result.get("username"));

            if (billType.equals("expense")) {
                if (hasRecordedExpense) {
                    assertNotNull(result.get("lastExpense"));
                }
                hasRecordedExpense = true;
            } else {
                if (hasRecordedIncome) {
                    assertNotNull(result.get("lastIncome"));
                }
                hasRecordedIncome = true;
            }

            BillItem billItem;
            if (billType.equals("expense")) {
                BillItem lastExpense = (BillItem) result.get("lastExpense");
                billItem = billItemDao.loadItem(lastExpense.getId());
                assertNotNull(billItem);
                assertEquals(userId, billItem.getUserId());
                assertEquals(categoryA.getId(), billItem.getCategoryId());
                assertEquals(billType, billItem.getBillType());
                assertEquals(amount, billItem.getAmount());
                assertEquals(description, billItem.getDescription());
            } else if (billType.equals("income")) {
                BillItem lastIncome = (BillItem) result.get("lastIncome");
                billItem = billItemDao.loadItem(lastIncome.getId());
                assertNotNull(billItem);
                assertEquals(userId, billItem.getUserId());
                assertEquals(categoryA.getId(), billItem.getCategoryId());
                assertEquals(billType, billItem.getBillType());
                assertEquals(amount, billItem.getAmount());
                assertEquals(description, billItem.getDescription());
            }

            User user = userDao.loadUser(userId);
            assertNotNull(user);
            long diffInMillis = Math.abs(user.getLastBillTime().getTime() - billDate.getTime());
            assertTrue(diffInMillis <= TimeUnit.SECONDS.toMillis(1), "Expected and actual dates differ by more than 1 second");

            if (billType.equals("expense")) {
                totalExpenseIncrease += amount;
                BillItem lastUserExpense = userDao.getLastUserExpense(userId);
                assertNotNull(lastUserExpense);
                assertEquals(amount, lastUserExpense.getAmount());
                long expenseDiffInMillis = Math.abs(lastUserExpense.getBillDate().getTime() - billDate.getTime());
                assertTrue(expenseDiffInMillis <= TimeUnit.SECONDS.toMillis(1), "Expected and actual expense dates differ by more than 1 second");
            } else {
                totalIncomeIncrease += amount;
                BillItem lastUserIncome = userDao.getLastUserIncome(userId);
                assertNotNull(lastUserIncome);
                assertEquals(amount, lastUserIncome.getAmount());
                long incomeDiffInMillis = Math.abs(lastUserIncome.getBillDate().getTime() - billDate.getTime());
                assertTrue(incomeDiffInMillis <= TimeUnit.SECONDS.toMillis(1), "Expected and actual income dates differ by more than 1 second");
            }
        }

        int expectedTotalExpense = initialTotalExpense + totalExpenseIncrease;
        int expectedTotalIncome = initialTotalIncome + totalIncomeIncrease;

        expenses = userDao.listUserExpenses(userId);
        incomes = userDao.listUserIncomes(userId);
        int actualTotalExpense = expenses.stream().mapToInt(BillItem::getAmount).sum();
        int actualTotalIncome = incomes.stream().mapToInt(BillItem::getAmount).sum();

        assertEquals(expectedTotalExpense, actualTotalExpense);
        assertEquals(expectedTotalIncome, actualTotalIncome);
    }

}
