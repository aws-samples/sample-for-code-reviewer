package demo.great.dao.impl;

import demo.great.base.GreatException;
import demo.great.config.DataSourceContextHolder;
import demo.great.dao.BillCategoryDao;
import demo.great.dao.mapper.BillCategoryMapper;
import demo.great.entity.BillCategory;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public class BillCategoryDaoImpl implements BillCategoryDao {
    private static final Logger logger = LoggerFactory.getLogger(BillCategoryDaoImpl.class);

    @Autowired
    private BillCategoryMapper billCategoryMapper;

    @Override
    public int createCategory(BillCategory category) {
        DataSourceContextHolder.write();
        try {
            billCategoryMapper.createCategory(category);
            return category.getId();
        } catch (Exception e) {
            logger.error("Failed to create category", e);
            throw new GreatException("Failed to create category", e);
        } finally {
            DataSourceContextHolder.clearDataSourceType();
        }
    }

    @Override
    public int updateCategory(BillCategory category) {
        DataSourceContextHolder.write();
        try {
            int rowsUpdated = billCategoryMapper.updateCategory(category);
            if (rowsUpdated > 0) {
                return category.getId();
            } else {
                throw new GreatException("Category not found with id: " + category.getId());
            }
        } catch (Exception e) {
            logger.error("Failed to update category", e);
            throw new GreatException("Failed to update category", e);
        } finally {
            DataSourceContextHolder.clearDataSourceType();
        }
    }

    @Override
    public int deleteCategory(Integer id) {
        DataSourceContextHolder.write();
        try {
            int rowsDeleted = billCategoryMapper.deleteCategory(id);
            return rowsDeleted;
        } catch (Exception e) {
            logger.error("Failed to delete category", e);
            throw new GreatException("Failed to delete category", e);
        } finally {
            DataSourceContextHolder.clearDataSourceType();
        }
    }

    @Override
    public BillCategory loadCategory(Integer id) {
        DataSourceContextHolder.read();
        try {
            return billCategoryMapper.loadCategory(id);
        } catch (Exception e) {
            logger.error("Failed to load category", e);
            throw new GreatException("Failed to load category", e);
        } finally {
            DataSourceContextHolder.clearDataSourceType();
        }
    }

    @Override
    public BillCategory loadCategory(Integer id, boolean master) {
        if (master) {
            DataSourceContextHolder.write();
        } else {
            DataSourceContextHolder.read();
        }
        try {
            return billCategoryMapper.loadCategory(id);
        } catch (Exception e) {
            logger.error("Failed to load category", e);
            throw new GreatException("Failed to load category", e);
        } finally {
            DataSourceContextHolder.clearDataSourceType();
        }
    }

    @Override
    public List<BillCategory> listCategories(String name) {
        DataSourceContextHolder.read();
        try {
            return billCategoryMapper.listCategories(name);
        } catch (Exception e) {
            logger.error("Failed to list categories", e);
            throw new GreatException("Failed to list categories", e);
        } finally {
            DataSourceContextHolder.clearDataSourceType();
        }
    }

    @Override
    public List<BillCategory> listCategories(String name, boolean master) {
        if (master) {
            DataSourceContextHolder.write();
        } else {
            DataSourceContextHolder.read();
        }
        try {
            return billCategoryMapper.listCategories(name);
        } catch (Exception e) {
            logger.error("Failed to list categories", e);
            throw new GreatException("Failed to list categories", e);
        } finally {
            DataSourceContextHolder.clearDataSourceType();
        }
    }
}
