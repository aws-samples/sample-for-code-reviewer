package demo.great.dao;

import demo.great.entity.BillCategory;

import java.util.List;

public interface BillCategoryDao {
    int createCategory(BillCategory category);
    int updateCategory(BillCategory category);
    int deleteCategory(Integer id);
    BillCategory loadCategory(Integer id);
    BillCategory loadCategory(Integer id, boolean master);
    List<BillCategory> listCategories(String name);
    List<BillCategory> listCategories(String name, boolean master);
}
