package demo.great.dao.impl;

import demo.great.base.GreatException;
import demo.great.config.DataSourceContextHolder;
import demo.great.dao.BillItemDao;
import demo.great.dao.mapper.BillItemMapper;
import demo.great.entity.BillItem;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;

import java.util.Date;
import java.util.List;

@Repository
public class BillItemDaoImpl implements BillItemDao {
    private static final Logger logger = LoggerFactory.getLogger(BillItemDaoImpl.class);

    @Autowired
    private BillItemMapper billItemMapper;

    @Override
    public int createItem(BillItem item) {
        DataSourceContextHolder.write();
        try {
            billItemMapper.createItem(item);
            return item.getId();
        } catch (Exception e) {
            logger.error("Failed to create bill item", e);
            throw new GreatException("Failed to create bill item", e);
        } finally {
            DataSourceContextHolder.clearDataSourceType();
        }
    }

    @Override
    public int updateItem(BillItem item) {
        DataSourceContextHolder.write();
        try {
            int rowsUpdated = billItemMapper.updateItem(item);
            if (rowsUpdated > 0) {
                return item.getId();
            } else {
                throw new GreatException("Bill item not found with id: " + item.getId());
            }
        } catch (Exception e) {
            logger.error("Failed to update bill item", e);
            throw new GreatException("Failed to update bill item", e);
        } finally {
            DataSourceContextHolder.clearDataSourceType();
        }
    }

    @Override
    public int deleteItem(Integer id) {
        DataSourceContextHolder.write();
        try {
            int rowsDeleted = billItemMapper.deleteItem(id);
            return rowsDeleted;
        } catch (Exception e) {
            logger.error("Failed to delete bill item", e);
            throw new GreatException("Failed to delete bill item", e);
        } finally {
            DataSourceContextHolder.clearDataSourceType();
        }
    }

    @Override
    public BillItem loadItem(Integer id) {
        DataSourceContextHolder.read();
        try {
            return billItemMapper.loadItem(id);
        } catch (Exception e) {
            logger.error("Failed to load bill item", e);
            throw new GreatException("Failed to load bill item", e);
        } finally {
            DataSourceContextHolder.clearDataSourceType();
        }
    }

    @Override
    public BillItem loadItem(Integer id, boolean master) {
        if (master) {
            DataSourceContextHolder.write();
        } else {
            DataSourceContextHolder.read();
        }
        try {
            return billItemMapper.loadItem(id);
        } catch (Exception e) {
            logger.error("Failed to load bill item", e);
            throw new GreatException("Failed to load bill item", e);
        } finally {
            DataSourceContextHolder.clearDataSourceType();
        }
    }

    @Override
    public List<BillItem> listItems(Integer userId, Integer categoryId, Date startDate, Date endDate, String billType) {
        DataSourceContextHolder.read();
        try {
            return billItemMapper.listItems(userId, categoryId, startDate, endDate, billType);
        } catch (Exception e) {
            logger.error("Failed to list bill items", e);
            throw new GreatException("Failed to list bill items", e);
        } finally {
            DataSourceContextHolder.clearDataSourceType();
        }
    }

    @Override
    public List<BillItem> listItems(Integer userId, Integer categoryId, Date startDate, Date endDate, String billType, boolean master) {
        if (master) {
            DataSourceContextHolder.write();
        } else {
            DataSourceContextHolder.read();
        }
        try {
            return billItemMapper.listItems(userId, categoryId, startDate, endDate, billType);
        } catch (Exception e) {
            logger.error("Failed to list bill items", e);
            throw new GreatException("Failed to list bill items", e);
        } finally {
            DataSourceContextHolder.clearDataSourceType();
        }
    }
}
