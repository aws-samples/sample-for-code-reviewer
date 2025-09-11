package demo.great.service;

import demo.great.base.GreatException;
import demo.great.dao.BillItemDao;
import demo.great.entity.BillItem;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.Date;
import java.util.List;

@Service
public class BillItemService {
    private static final Logger logger = LoggerFactory.getLogger(BillItemService.class);

    @Autowired
    private BillItemDao billItemDao;

    public int createItem(Integer userId, Integer categoryId, Date billDate, String billType, Integer amount, String description) {
        try {
            BillItem item = new BillItem();
            item.setUserId(userId);
            item.setCategoryId(categoryId);
            item.setBillDate(billDate);
            item.setBillType(billType);
            item.setAmount(amount);
            item.setDescription(description);
            return billItemDao.createItem(item);
        } catch (Exception e) {
            logger.error("Failed to create bill item", e);
            throw new GreatException("Failed to create bill item", e);
        }
    }

    public int updateItem(Integer id, Integer userId, Integer categoryId, Date billDate, String billType, Integer amount, String description) {
        try {
            BillItem item = billItemDao.loadItem(id, true);
            if (item == null) {
                throw new GreatException("Bill item not found with id: " + id);
            }
            item.setUserId(userId);
            item.setCategoryId(categoryId);
            item.setBillDate(billDate);
            item.setBillType(billType);
            item.setAmount(amount);
            item.setDescription(description);
            return billItemDao.updateItem(item);
        } catch (Exception e) {
            logger.error("Failed to update bill item", e);
            throw new GreatException("Failed to update bill item", e);
        }
    }

    public int deleteItem(Integer id) {
        try {
            int rowsDeleted = billItemDao.deleteItem(id);
            return rowsDeleted > 0 ? id : 0;
        } catch (Exception e) {
            logger.error("Failed to delete bill item", e);
            throw new GreatException("Failed to delete bill item", e);
        }
    }

    public BillItem loadItem(Integer id) {
        try {
            return billItemDao.loadItem(id);
        } catch (Exception e) {
            logger.error("Failed to load bill item", e);
            throw new GreatException("Failed to load bill item", e);
        }
    }

    public List<BillItem> listItems(Integer userId, Integer categoryId, Date startDate, Date endDate, String billType) {
        try {
            return billItemDao.listItems(userId, categoryId, startDate, endDate, billType);
        } catch (Exception e) {
            logger.error("Failed to list bill items", e);
            throw new GreatException("Failed to list bill items", e);
        }
    }
}
