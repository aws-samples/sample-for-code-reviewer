package demo.great.service;

import demo.great.base.GreatException;
import demo.great.dao.BillCategoryDao;
import demo.great.entity.BillCategory;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class BillCategoryService {
    private static final Logger logger = LoggerFactory.getLogger(BillCategoryService.class);

    @Autowired
    private BillCategoryDao billCategoryDao;

    public int createCategory(String name, String description) {
        try {
            BillCategory category = new BillCategory();
            category.setName(name);
            category.setDescription(description);
            return billCategoryDao.createCategory(category);
        } catch (Exception e) {
            logger.error("Failed to create category", e);
            throw new GreatException("Failed to create category", e);
        }
    }

    public int updateCategory(Integer id, String name, String description) {
        try {
            BillCategory category = billCategoryDao.loadCategory(id, true);
            if (category == null) {
                throw new GreatException("Category not found with id: " + id);
            }
            category.setName(name);
            category.setDescription(description);
            return billCategoryDao.updateCategory(category);
        } catch (Exception e) {
            logger.error("Failed to update category", e);
            throw new GreatException("Failed to update category", e);
        }
    }

    public int deleteCategory(Integer id) {
        try {
            int rowsDeleted = billCategoryDao.deleteCategory(id);
            return rowsDeleted > 0 ? id : 0;
        } catch (Exception e) {
            logger.error("Failed to delete category", e);
            throw new GreatException("Failed to delete category", e);
        }
    }

    public BillCategory loadCategory(Integer id) {
        try {
            return billCategoryDao.loadCategory(id);
        } catch (Exception e) {
            logger.error("Failed to load category", e);
            throw new GreatException("Failed to load category", e);
        }
    }

    public List<BillCategory> listCategories(String name) {
        try {
            return billCategoryDao.listCategories(name);
        } catch (Exception e) {
            logger.error("Failed to list categories", e);
            throw new GreatException("Failed to list categories", e);
        }
    }
}
