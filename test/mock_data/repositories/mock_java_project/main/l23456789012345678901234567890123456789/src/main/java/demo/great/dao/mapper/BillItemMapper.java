package demo.great.dao.mapper;

import demo.great.entity.BillItem;
import org.apache.ibatis.annotations.Mapper;
import java.util.List;

/**
 * 账单项Mapper接口
 * 
 * @author demo
 */
@Mapper
public interface BillItemMapper {
    
    /**
     * 根据ID查询账单项
     */
    BillItem selectById(Long id);
    
    /**
     * 查询所有账单项
     */
    List<BillItem> selectAll();
    
    /**
     * 插入账单项
     */
    int insert(BillItem item);
    
    /**
     * 更新账单项
     */
    int update(BillItem item);
    
    /**
     * 删除账单项
     */
    int deleteById(Long id);
    
    /**
     * 根据用户ID查询账单项
     */
    List<BillItem> selectByUserId(Long userId);
    
    /**
     * 根据分类ID查询账单项
     */
    List<BillItem> selectByCategoryId(Long categoryId);
}