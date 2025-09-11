package demo.great.dao.mapper;

import demo.great.entity.BillCategory;
import org.apache.ibatis.annotations.Mapper;

import java.util.List;

@Mapper
public interface BillCategoryMapper {
    int createCategory(BillCategory category);
    int updateCategory(BillCategory category);
    int deleteCategory(Integer id);
    BillCategory loadCategory(Integer id);
    List<BillCategory> listCategories(String name);
}
