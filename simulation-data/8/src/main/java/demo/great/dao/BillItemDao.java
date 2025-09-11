package demo.great.dao;

import demo.great.entity.BillItem;

import java.util.Date;
import java.util.List;

public interface BillItemDao {
    int createItem(BillItem item);
    int updateItem(BillItem item);
    int deleteItem(Integer id);
    BillItem loadItem(Integer id);
    BillItem loadItem(Integer id, boolean master);
    List<BillItem> listItems(Integer userId, Integer categoryId, Date startDate, Date endDate, String billType);
    List<BillItem> listItems(Integer userId, Integer categoryId, Date startDate, Date endDate, String billType, boolean master);
}
