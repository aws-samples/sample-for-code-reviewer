package demo.great.dao.mapper;

import demo.great.entity.BillCategory;
import org.apache.ibatis.annotations.Mapper;
import java.util.List;

/**
 * 账单分类Mapper接口
 * 
 * @author demo
 */
@Mapper
public interface BillCategoryMapper {
    
    /**
     * 根据ID查询分类
     */
    BillCategory selectById(Long id);
    
    /**
     * 查询所有分类
     */
    List<BillCategory> selectAll();
    
    /**
     * 插入分类
     */
    int insert(BillCategory category);
    
    /**
     * 更新分类
     */
    int update(BillCategory category);
    
    /**
     * 删除分类
     */
    int deleteById(Long id);
    
    /**
     * 根据名称查询分类
     */
    BillCategory selectByName(String name);
}